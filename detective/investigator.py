"""Investigator: one reasoning log per suspect, built from every earlier finding.

Each step has
  - a label: FACT (decided by records: badge log, login log, CCTV, brief),
             CLAIM (rests on what someone said or wrote),
             ASSUMPTION (an inference, e.g. a CCTV match by timing, or "no record means absent"),
             SPECULATION (a guess; always weight 0);
  - a weight: positive points toward the suspect, negative away;
  - exact quotes from the documents.

Rules enforced on every step, from the rules engine and from the LLM alike (see `validate`):
  quotes must exist word for word; a FACT may only cite records; SPECULATION weighs zero;
  weights stay within +-MAX_WEIGHT.

All weights live in WEIGHTS below so the scoring policy is in one place and easy to review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from .alibi import Alibi, AlibiCheck, Verdict
from .grounding import find_quote, verify
from .links import CCTVMatch, Connection
from .models import Case, EvidenceKind, Quote
from .motive import Motive, MotiveType
from .opportunity import Access, Opportunity, Window
from .records import Dispute
from .speculation import Speculation


class Label(str, Enum):
    FACT = "fact"
    CLAIM = "claim"
    ASSUMPTION = "assumption"
    SPECULATION = "speculation"


MAX_WEIGHT = 3.0
WEIGHTS = {
    "alibi_contradicted": 3.0,  # a record shows the suspect's own account is false
    "alibi_supported": -1.0,  # a record confirms part of an alibi that holds
    "alibi_consistent": -0.5,  # nothing contradicts it, but nothing confirms it
    "at_scene_undisclosed": 2.0,  # at the scene and did not say so
    "at_scene_disclosed": 0.5,  # at the scene, said so, and records agree
    "on_site": 0.0,
    "no_presence": -1.5,
    "cctv_match": 1.0,
    "connection": 1.0,
    "denied_connection": 2.0,
    "vouch_contradicted": 1.0,  # a friend's alibi for them is false too
    "vouch_supported": -0.5,
    "sighting_confirmed": 1.0,  # a witness saw them on the premises in the window, and records agree
    "sighting_unconfirmed": 0.5,  # a witness saw them there; no record confirms it
    MotiveType.INTENT: 2.0,
    MotiveType.GAIN: 1.5,
    MotiveType.MONEY: 1.0,
    MotiveType.CONFLICT: 0.5,
    MotiveType.NEED: 0.5,
}


@dataclass(frozen=True)
class Step:
    suspect: str
    kind: str  # alibi | sighting | conflict | opportunity | motive | link | connection | speculation | dispute | llm
    label: Label
    weight: float
    evidence: tuple[Quote, ...]
    text: str
    tested: Quote | None = None  # for alibi steps: the statement that was checked
    source: str = "rules"


@dataclass
class StepRejection:
    item: dict
    reason: str


@dataclass
class SuspectLog:
    suspect: str
    steps: list[Step] = field(default_factory=list)

    @property
    def score(self) -> float:
        return round(sum(s.weight for s in self.steps), 2)


@dataclass
class Assessment:
    logs: dict[str, SuspectLog]
    rejections: list[StepRejection] = field(default_factory=list)

    def ranking(self) -> list[SuspectLog]:
        return sorted(self.logs.values(), key=lambda l: (-l.score, l.suspect))

    @property
    def most_likely(self) -> str:
        return self.ranking()[0].suspect

    def confidence(self) -> tuple[str, str]:
        """(level, explanation). Level depends on the lead, on record-backed facts, and on how much of
        the lead would survive if every assumption turned out wrong."""
        level, reasons = self.confidence_reasons()
        return level, " ".join(reasons)

    def confidence_reasons(self) -> tuple[str, list[str]]:
        ranked = self.ranking()
        top = ranked[0]
        runner = ranked[1] if len(ranked) > 1 else None
        margin = top.score - (runner.score if runner else 0.0)
        facts = sum(s.weight for s in top.steps if s.label is Label.FACT and s.weight > 0)
        assumed = sum(s.weight for s in top.steps if s.label is Label.ASSUMPTION and s.weight > 0)
        claims = sum(s.weight for s in top.steps if s.label is Label.CLAIM and s.weight > 0)
        robust = margin - assumed
        if margin >= 5 and facts > 0 and robust >= 3:
            level = "high"
        elif margin >= 2 and (facts > 0 or margin >= 3):
            level = "medium"
        else:
            level = "low"
        reasons = [
            f"{top.suspect} leads {runner.suspect if runner else 'nobody'} by {margin:.1f} points.",
            f"Record-backed facts add {facts:+.1f}, statements add {claims:+.1f} and assumptions add {assumed:+.1f} "
            f"to {top.suspect}'s score.",
            f"If every assumption were wrong, the lead would be {robust:.1f} points.",
        ]
        if facts == 0:
            reasons.append("No record-backed fact points to them, so the case rests on statements and inference.")
        others = [l for l in ranked[1:] if l.score > 0]
        if others:
            reasons.append("Also above zero: " + ", ".join(f"{l.suspect} ({l.score:+.1f})" for l in others) + ".")
        return level, reasons


def validate(case: Case, step: Step) -> str | None:
    """Why a step breaks the rules, or None if it is acceptable."""
    if step.suspect not in {p.name for p in case.suspects}:
        return f"unknown suspect {step.suspect!r}"
    if not step.evidence:
        return "no quotes cited"
    if any(not verify(case, q) for q in step.evidence) or (step.tested and not verify(case, step.tested)):
        return "quote not found verbatim in the documents"
    if step.label is Label.FACT and any(case.documents[q.doc_id].kind is not EvidenceKind.RECORD for q in step.evidence):
        return "a fact may only cite records (badge log, login log, CCTV, brief)"
    if step.label is Label.SPECULATION and step.weight != 0:
        return "speculation must weigh zero"
    if abs(step.weight) > MAX_WEIGHT:
        return f"weight outside +-{MAX_WEIGHT}"
    return None


def _alibi_steps(name: str, alibi: Alibi) -> list[Step]:
    steps = []
    broken = alibi.status == "broken"
    for c in alibi.checks:
        ev = tuple(c.evidence)
        if c.claim.kind == "vouch":
            steps.append(_vouch_step(name, c))
            continue
        if c.verdict is Verdict.CONTRADICTED:
            steps.append(Step(name, "alibi", Label.FACT, WEIGHTS["alibi_contradicted"], ev,
                              f"Alibi contradicted: {c.explanation}", c.claim.quote))
        elif c.verdict is Verdict.SUPPORTED:
            weight = 0.0 if broken else WEIGHTS["alibi_supported"]
            note = " (does not help: another part of the same account is false)" if broken else ""
            steps.append(Step(name, "alibi", Label.FACT, weight, ev, f"Alibi supported{note}: {c.explanation}",
                              c.claim.quote))
        elif c.verdict is Verdict.CONSISTENT:
            weight = 0.0 if broken else WEIGHTS["alibi_consistent"]
            steps.append(Step(name, "alibi", Label.ASSUMPTION, weight, ev or (c.claim.quote,),
                              f"Alibi consistent, not confirmed: {c.explanation}", c.claim.quote))
        else:
            steps.append(Step(name, "alibi", Label.CLAIM, 0.0, (c.claim.quote,),
                              f"Alibi unverified: {c.explanation}", c.claim.quote))
    return steps


def _vouch_step(name: str, c: AlibiCheck) -> Step:
    by = c.claim.reported_by
    if c.verdict is Verdict.CONTRADICTED:
        return Step(name, "alibi", Label.FACT, WEIGHTS["vouch_contradicted"], tuple(c.evidence),
                    f"Alibi from {by} is false: {c.explanation}", c.claim.quote)
    if c.verdict is Verdict.SUPPORTED:
        return Step(name, "alibi", Label.FACT, WEIGHTS["vouch_supported"], tuple(c.evidence),
                    f"Alibi from {by} confirmed: {c.explanation}", c.claim.quote)
    return Step(name, "alibi", Label.CLAIM, 0.0, (c.claim.quote,),
                f"Alibi rests only on {by}'s word, which no record can confirm; it does not count as evidence.",
                c.claim.quote)


def _sighting_step(case: Case, name: str, c: AlibiCheck, window: Window | None) -> Step:
    claim, by = c.claim, c.claim.reported_by
    loc = case.location(claim.location)
    inside = window is None or window.start <= claim.start <= window.end
    relevant = bool(loc and loc.onsite and inside)
    if c.verdict is Verdict.SUPPORTED and relevant:
        return Step(name, "sighting", Label.FACT, WEIGHTS["sighting_confirmed"], tuple(c.evidence),
                    f"{by} saw {name} at {claim.location}, and records agree: {c.explanation}", claim.quote)
    if c.verdict is Verdict.CONTRADICTED:
        return Step(name, "sighting", Label.CLAIM, 0.0, (claim.quote,),
                    f"{by}'s sighting of {name} is contradicted by records: {c.explanation}", claim.quote)
    weight = WEIGHTS["sighting_unconfirmed"] if relevant else 0.0
    return Step(name, "sighting", Label.CLAIM, weight, (claim.quote,),
                f"{by} says they saw {name} at {claim.location}; no record confirms it.", claim.quote)


def _opportunity_step(name: str, opp: Opportunity, alibi: Alibi, window: Window) -> Step:
    if opp.access is Access.AT_SCENE:
        disclosed = any(
            c.verdict is Verdict.SUPPORTED and c.claim.location == window.scene and set(c.evidence) & set(opp.evidence)
            for c in alibi.checks
        )
        key = "at_scene_disclosed" if disclosed else "at_scene_undisclosed"
        note = " They said so themselves and the records agree." if disclosed else " They never mentioned it."
        return Step(name, "opportunity", Label.FACT, WEIGHTS[key], tuple(opp.evidence), opp.explanation + note)
    if opp.access is Access.ON_SITE:
        return Step(name, "opportunity", Label.FACT, WEIGHTS["on_site"], tuple(opp.evidence), opp.explanation)
    ev = tuple(opp.evidence) or (window.start_quote, window.end_quote)
    return Step(name, "opportunity", Label.ASSUMPTION, WEIGHTS["no_presence"], ev,
                opp.explanation + " (absence of records, not proof of absence)")


def assess(
    case: Case,
    alibis: dict[str, Alibi],
    opportunity: dict[str, Opportunity],
    window: Window | None,
    motives: list[Motive],
    matches: list[CCTVMatch],
    connections: list[Connection],
    speculation: list[Speculation],
    disputes: list[Dispute],
    conflicts: list | None = None,
) -> Assessment:
    logs = {p.name: SuspectLog(p.name) for p in case.suspects}
    for name, log in logs.items():
        log.steps += _alibi_steps(name, alibis[name])
        log.steps += [_sighting_step(case, name, c, window) for c in alibis[name].sightings]
        for conflict in (x for x in conflicts or [] if x.person == name):
            log.steps.append(Step(name, "conflict", Label.CLAIM, 0.0,
                                  (conflict.a.claim.quote, conflict.b.claim.quote),
                                  f"Statements conflict: {conflict.explanation()}"))
        if window and name in opportunity:
            log.steps.append(_opportunity_step(name, opportunity[name], alibis[name], window))

        counted: set[MotiveType] = set()
        for m in (m for m in motives if m.person == name):
            weight = 0.0 if m.type in counted else WEIGHTS[m.type]
            counted.add(m.type)
            again = " (already counted)" if weight == 0 else ""
            log.steps.append(Step(name, "motive", Label.CLAIM, weight, (m.quote,), f"Motive: {m.describe()}{again}"))

        for x in (x for x in matches if x.person == name):
            ev = (x.cctv, *x.records) + ((x.refers_to,) if x.refers_to else ())
            log.steps.append(Step(name, "link", Label.ASSUMPTION, WEIGHTS["cctv_match"], tuple(dict.fromkeys(ev)),
                                  f"Unnamed person on CCTV matched by timing: {x.explanation()}"))

        for c in (c for c in connections if c.suspect == name):
            log.steps.append(Step(name, "connection", Label.CLAIM, WEIGHTS["connection"], tuple(c.messages),
                                  f"Hidden connection: {c.explanation()}"))
            if c.denial:
                log.steps.append(Step(name, "connection", Label.CLAIM, WEIGHTS["denied_connection"],
                                      (c.denial, *c.messages),
                                      f"Denied contact with {c.party}, but recovered messages show it.", c.denial))

        for s in (s for s in speculation if name in s.about):
            log.steps.append(Step(name, "speculation", Label.SPECULATION, 0.0, (s.quote,),
                                  f"{s.speaker} {s.category}: \"{s.marker}\". Not evidence; weighs nothing."))

        for d in (d for d in disputes if d.person == name):
            log.steps.append(Step(name, "dispute", Label.FACT, 0.0, (d.record, d.cctv),
                                  f"Badge record disputed and left out: {d.explanation}"))

    for log in logs.values():
        for step in log.steps:
            if (reason := validate(case, step)) is not None:
                raise AssertionError(f"rules engine produced an invalid step ({reason}): {step}")
    return Assessment(logs)


# --- Optional LLM investigator -------------------------------------------------------------

# propose(case, assessment) -> list of {"suspect", "label", "weight", "quotes": [{"doc", "text"}], "reasoning"}
StepProposer = Callable[[Case, Assessment], list[dict]]


def add_llm_steps(case: Case, assessment: Assessment, propose: StepProposer) -> Assessment:
    """Ask the LLM for extra reasoning steps; keep only those that pass the same rules."""
    for item in propose(case, assessment):
        def reject(reason: str) -> None:
            assessment.rejections.append(StepRejection(item, reason))

        try:
            label = Label(item.get("label"))
            weight = float(item.get("weight", 0))
        except (ValueError, TypeError):
            reject(f"invalid label or weight: {item.get('label')!r} / {item.get('weight')!r}")
            continue
        quotes = []
        for q in item.get("quotes") or []:
            found = find_quote(case, q.get("doc", ""), q.get("text", ""))
            if found is None:
                break
            quotes.append(found)
        else:
            step = Step(item.get("suspect", ""), "llm", label, weight, tuple(quotes),
                        str(item.get("reasoning", "")), source="llm")
            if (reason := validate(case, step)) is not None:
                reject(reason)
            else:
                assessment.logs[step.suspect].steps.append(step)
            continue
        reject("quote not found verbatim in the documents")
    return assessment
