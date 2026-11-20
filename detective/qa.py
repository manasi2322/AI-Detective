"""Follow-up questions: answer an investigator's questions from the findings, with checked citations.

    "Did Sam lie?"                      -> his statements that records contradict (or confirm)
    "Where was Marcus at 19:45?"        -> what the records show, then what people said
    "Who was in the Design Lab at 20:50?"
    "What is Marcus's motive?"  "Is Priya's alibi solid?"  "Why not Lena?"  "Who did it?"
    "How confident are you?"  "What contradictions are there?"  "What happened at 19:58?"
    anything else                       -> the most relevant evidence passages, no conclusion drawn

Answers are built from the same structured findings as the report, never from free text, so every
sentence points at quotes that exist. Each citation is tagged with what kind of evidence it is:
record, statement, assumption or speculation. `answer_with_llm` lets Claude phrase an answer from
the retrieved evidence; any quote it gives that is not in the documents is dropped and reported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from .alibi import AlibiCheck, Verdict
from .grounding import find_quote
from .investigator import Label
from .models import EvidenceKind, Quote
from .timeparse import find_times

NEAR = timedelta(minutes=30)


@dataclass
class Answer:
    question: str
    intent: str
    text: str
    citations: list[tuple[str, Quote]] = field(default_factory=list)  # (kind, quote)
    source: str = "rules"
    rejected: list[str] = field(default_factory=list)

    def cite(self, kind: str, *quotes: Quote) -> None:
        for q in quotes:
            if q is not None and (kind, q) not in self.citations:
                self.citations.append((kind, q))

    def render(self) -> str:
        out = [self.text]
        if self.citations:
            out.append("")
            out.append("Evidence:")
            for kind, q in self.citations:
                out.append(f"  [{kind}] “{q.text}” [{q.cite()}]")
        if self.rejected:
            out.append("")
            out.append(f"Dropped {len(self.rejected)} quote(s) the LLM gave that are not in the documents:")
            out += [f"  - {r}" for r in self.rejected]
        return "\n".join(out)


def _kind_of(inv, q: Quote) -> str:
    return "record" if inv.index.case.documents[q.doc_id].kind is EvidenceKind.RECORD else "statement"


class _Resolver:
    """Find people, places and a time in a question, case-insensitively."""

    def __init__(self, inv):
        case = inv.index.case
        self.inv = inv
        self._people = self._table({p.name: (p.name, *p.aliases) for p in case.people})
        self._places = self._table({l.name: (l.name, *l.aliases) for l in case.locations})

    @staticmethod
    def _table(names: dict[str, tuple[str, ...]]):
        alias = {a.lower(): n for n, aliases in names.items() for a in aliases}
        ordered = sorted(alias, key=len, reverse=True)
        return re.compile(r"\b(" + "|".join(re.escape(a) for a in ordered) + r")(?:'s)?\b", re.I), alias

    @staticmethod
    def _find(table, text: str) -> list[str]:
        pattern, alias = table
        return list(dict.fromkeys(alias[m.group(1).lower()] for m in pattern.finditer(text)))

    def people(self, text: str) -> list[str]:
        return self._find(self._people, text)

    def places(self, text: str) -> list[str]:
        return self._find(self._places, text)

    def time(self, text: str) -> datetime | None:
        times = find_times(text, self.inv.index.case.incident_date)
        if not times:
            return None
        t = times[0].time
        w = self.inv.window
        if w and t < w.start and w.start <= t + timedelta(days=1) <= w.end:
            t += timedelta(days=1)  # "08:45" in an overnight case means the next morning
        return t


_INTENTS = [
    ("confidence", r"\b(confiden\w*|how sure|certain)\b"),
    ("lie", r"\b(lie|lied|lies|lying|liar|truthful|honest|telling the truth)\b"),
    ("where", r"\bwhere\b"),
    ("who_at", r"\bwho\b.*\b(in|at|inside|near)\b"),
    ("motive", r"\b(motive|motives|reason to|why would)\b"),
    ("alibi", r"\balibi"),
    ("connections", r"\b(connect\w*|contact\w*|in touch|linked|links?|know each other)\b"),
    ("contradictions", r"\b(contradict\w*|conflict\w*|inconsisten\w*)\b"),
    ("opportunity", r"\b(opportunit\w*|access|could have)\b"),
    ("why", r"\bwhy\b"),
    ("culprit", r"\b(who (did it|stole|took|leaked|swapped|is (the )?(culprit|thief))|most likely|prime suspect|whodunit)\b"),
    ("what_happened", r"\b(what happened|timeline|what was going on)\b"),
]


def ask(inv, question: str) -> Answer:
    r = _Resolver(inv)
    q = question.lower()
    people, places, t = r.people(question), r.places(question), r.time(question)
    for intent, pattern in _INTENTS:
        if re.search(pattern, q):
            handler = _HANDLERS[intent]
            answer = handler(inv, question, people, places, t)
            if answer is not None:
                return answer
    if t is not None and not people:
        return _what_happened(inv, question, people, places, t)
    if people and len(people) == 1 and re.search(r"\b(about|tell me|explain)\b", q):
        return _why(inv, question, people, places, t)
    return _search(inv, question)


def _need_person(inv, question: str, intent: str) -> Answer:
    names = ", ".join(p.name for p in inv.index.case.people)
    m = re.search(r"\b(?:was|did|is|does|has|about|not)\s+([A-Z][a-z]+)\b", question)
    if m:
        return Answer(question, intent, f"Nobody called {m.group(1)} appears in this case, so there is no evidence "
                                        f"about them. People in this case: {names}.")
    return Answer(question, intent, f"I couldn't tell who the question is about. People in this case: {names}.")


# --- handlers --------------------------------------------------------------------------------

def _statements_by(inv, person: str) -> list[AlibiCheck]:
    """Every checked statement this person made: their own account, alibis they gave, sightings they reported."""
    out = []
    for alibi in inv.alibis.values():
        for c in alibi.checks + alibi.sightings:
            if (c.claim.reported_by or c.claim.person) == person:
                out.append(c)
    return out


def _lie(inv, question, people, places, t) -> Answer:
    if not people:
        return _need_person(inv, question, "lie")
    p = people[0]
    a = Answer(question, "lie", "")
    checks = _statements_by(inv, p)
    false = [c for c in checks if c.verdict is Verdict.CONTRADICTED]
    denials = [c for c in inv.connections if c.suspect == p and c.denial]
    if false or denials:
        n = len(false) + len(denials)
        lines = [f"Yes. {n} statement{'s' if n > 1 else ''} by {p} {'are' if n > 1 else 'is'} contradicted by the evidence:"]
        for c in false:
            lines.append(f"- “{c.claim.quote.text}” [{c.claim.quote.cite()}]: {c.explanation}")
            a.cite("statement", c.claim.quote)
            a.cite("record", *c.evidence)
        for c in denials:
            lines.append(f"- “{c.denial.text}” [{c.denial.cite()}]: recovered messages show contact with {c.party}.")
            a.cite("statement", c.denial)
            a.cite("statement", *c.messages)
        lines.append("A contradiction shows a statement is false; it does not by itself show why they lied.")
        a.text = "\n".join(lines)
        return a
    if not checks:
        a.text = f"No contradiction found, but {p} made no statements about times and places that records could check."
        return a
    good = [c for c in checks if c.verdict is Verdict.SUPPORTED]
    soft = [c for c in checks if c.verdict in (Verdict.CONSISTENT, Verdict.UNVERIFIED)]
    lines = [f"No. None of {p}'s {len(checks)} checkable statements is contradicted by records."]
    for c in good:
        lines.append(f"- Confirmed: “{c.claim.quote.text}” [{c.claim.quote.cite()}]: {c.explanation}")
        a.cite("statement", c.claim.quote)
        a.cite("record", *c.evidence)
    for c in soft:
        lines.append(f"- Not confirmable: “{c.claim.quote.text}” [{c.claim.quote.cite()}]: {c.explanation}")
        a.cite("statement", c.claim.quote)
    if soft:
        lines.append("Statements that records can't confirm could still be false.")
    a.text = "\n".join(lines)
    return a


def _where(inv, question, people, places, t) -> Answer | None:
    if not people:
        return None if places else _need_person(inv, question, "where")
    p = people[0]
    a = Answer(question, "where", "")
    if t is None:
        moves = inv.presence.movements(p)
        lines = [f"Records for {p}:" if moves else f"No movement records for {p}."]
        for m in moves:
            lines.append(f"- {m.time:%m-%d %H:%M} at {m.location or '?'} [{m.quote.cite()}]")
            a.cite("record", m.quote)
        lines.append("Ask with a time (\"Where was ... at 19:45?\") for a specific moment.")
        a.text = "\n".join(lines)
        return a
    state, why = inv.presence.state_at(p, t)
    lines = [f"At {t:%H:%M} on {t:%m-%d}, the records put {p} {_state_words(state)}."]
    a.cite("record", *why)
    near = [m for m in inv.presence.movements(p) if abs(m.time - t) <= NEAR]
    for m in near:
        lines.append(f"- Record {m.time:%H:%M}: {m.location or '?'} [{m.quote.cite()}]")
        a.cite("record", m.quote)
    for d in inv.disputes:
        if d.person == p and abs(_time_of(inv, d.record) - t) <= NEAR:
            lines.append(f"- Set aside: a record at {_time_of(inv, d.record):%H:%M} is disputed and not used. "
                         f"{d.explanation}")
            a.cite("record", d.record, d.cctv)
    for match in inv.cctv_matches:
        if match.person == p and abs(_time_of(inv, match.cctv) - t) <= NEAR:
            lines.append(f"- Assumption: an unnamed person on CCTV at {_time_of(inv, match.cctv):%H:%M} "
                         f"is probably {p} ({match.explanation()})")
            a.cite("assumption", match.cctv)
    said = []
    for alibi in inv.alibis.values():
        for c in alibi.checks + alibi.sightings:
            cl = c.claim
            if cl.person == p and cl.start - NEAR / 2 <= t <= (cl.end or cl.start) + NEAR / 2:
                said.append(c)
    for c in said:
        who = c.claim.reported_by or p
        lines.append(f"- {who} said: “{c.claim.quote.text}” [{c.claim.quote.cite()}], which is {c.verdict.value} "
                     f"by the records.")
        a.cite("statement", c.claim.quote)
    if not near and not said and state == "unknown":
        lines.append("Nothing in the evidence says where they were at that time.")
    a.text = "\n".join(lines)
    return a


def _state_words(state: str) -> str:
    return {"on site": "on the premises", "off site": "off the premises",
            "unknown": "nowhere in particular (no records either way)"}[state]


def _time_of(inv, q: Quote) -> datetime:
    return next(e.time for e in inv.index.events if e.quote == q)


def _who_at(inv, question, people, places, t) -> Answer | None:
    if not places and t is None:
        return None
    a = Answer(question, "who_at", "")
    case = inv.index.case
    lo, hi = (t - timedelta(minutes=15), t + timedelta(minutes=15)) if t else (None, None)
    lines = []
    if places:
        place = places[0]
        found = []
        for p in case.people:
            for m in inv.presence.movements(p.name):
                if m.location == place and (t is None or lo <= m.time <= hi):
                    found.append(m)
        when = f" around {t:%H:%M}" if t else ""
        if found:
            lines.append(f"Records put these people at {place}{when}:")
            for m in sorted(found, key=lambda m: m.time):
                lines.append(f"- {m.person} at {m.time:%m-%d %H:%M} [{m.quote.cite()}]")
                a.cite("record", m.quote)
        else:
            lines.append(f"No record puts anyone at {place}{when}.")
        for match in inv.cctv_matches:
            e = next(e for e in inv.index.events if e.quote == match.cctv)
            if e.location == place and (t is None or lo <= e.time <= hi):
                who = match.person or "nobody (no unique match)"
                lines.append(f"- Unnamed person on CCTV at {e.time:%H:%M}: probably {who} (assumption)")
                a.cite("assumption", match.cctv)
    else:
        on = []
        for p in case.people:
            state, why = inv.presence.state_at(p.name, t)
            if state == "on site":
                on.append(p.name)
                a.cite("record", *why)
        lines.append(f"Records put these people on the premises at {t:%H:%M}: {', '.join(on) or 'nobody'}.")
    lines.append("People who leave through an unbadged door may be missing from the records.")
    a.text = "\n".join(lines)
    return a


def _motive(inv, question, people, places, t) -> Answer:
    a = Answer(question, "motive", "")
    targets = people or [p.name for p in inv.index.case.suspects]
    lines = []
    for p in targets:
        ms = [m for m in inv.motives if m.person == p]
        if not ms:
            if people:
                lines.append(f"No motive for {p} appears in the evidence (guesses are not counted).")
            continue
        for m in ms:
            lines.append(f"- {p}: {m.describe()} [{m.quote.cite()}]")
            a.cite("statement", m.quote)
    if not lines:
        lines.append("No motives found in the evidence.")
    spec = [s for s in inv.speculation if not people or set(s.about) & set(people)]
    for s in spec:
        lines.append(f"- Not counted: {s.speaker}'s guess about {', '.join(s.about)} [{s.quote.cite()}]")
        a.cite("speculation", s.quote)
    a.text = "\n".join(lines)
    return a


def _alibi(inv, question, people, places, t) -> Answer:
    if not people:
        return _need_person(inv, question, "alibi")
    p = people[0]
    alibi = inv.alibis[p]
    a = Answer(question, "alibi", "")
    if not alibi.checks:
        a.text = f"{p} gave no account of their whereabouts that records could check."
        return a
    lines = [f"{p}'s alibi {_status_words(alibi.status)}:"]
    for c in alibi.checks:
        by = f" (given by {c.claim.reported_by})" if c.claim.reported_by else ""
        lines.append(f"- {c.verdict.value.upper()}{by}: “{c.claim.quote.text}” [{c.claim.quote.cite()}]. {c.explanation}")
        a.cite("statement", c.claim.quote)
        a.cite(_kind_of(inv, c.evidence[0]) if c.evidence else "record", *c.evidence)
    a.text = "\n".join(lines)
    return a


def _status_words(status: str) -> str:
    return {"broken": "is broken: records contradict part of it", "holds": "holds: nothing in the records contradicts it",
            "unverified": "can't be checked against the records", "no claims": "was never given"}[status]


def _connections(inv, question, people, places, t) -> Answer:
    a = Answer(question, "connections", "")
    lines = []
    for c in inv.connections:
        if people and c.suspect not in people and c.party not in people:
            continue
        lines.append(f"- {c.explanation()}")
        a.cite("statement", *c.messages)
        if c.denial:
            a.cite("statement", c.denial)
    for m in inv.cctv_matches:
        if m.person and (not people or m.person in people):
            lines.append(f"- CCTV [{m.cctv.cite()}] linked to {m.person} by timing (assumption).")
            a.cite("assumption", m.cctv)
    a.text = "\n".join(lines) if lines else "No hidden connections found."
    return a


def _contradictions(inv, question, people, places, t) -> Answer:
    a = Answer(question, "contradictions", "")
    lines = []
    for alibi in inv.alibis.values():
        for c in alibi.checks + alibi.sightings:
            if c.verdict is Verdict.CONTRADICTED and (not people or {c.claim.person, c.claim.reported_by} & set(people)):
                who = c.claim.reported_by or c.claim.person
                lines.append(f"- {who}: “{c.claim.quote.text}” [{c.claim.quote.cite()}] vs records: {c.explanation}")
                a.cite("statement", c.claim.quote)
                a.cite("record", *c.evidence)
    for c in inv.conflicts:
        if not people or c.person in people:
            lines.append(f"- Witnesses disagree: {c.explanation()}")
            a.cite("statement", c.a.claim.quote, c.b.claim.quote)
    for c in inv.connections:
        if c.denial and (not people or c.suspect in people):
            lines.append(f"- {c.suspect} denied contact with {c.party} [{c.denial.cite()}], but messages show it.")
            a.cite("statement", c.denial, *c.messages)
    a.text = "\n".join(lines) if lines else "No contradictions found."
    return a


def _opportunity(inv, question, people, places, t) -> Answer:
    a = Answer(question, "opportunity", "")
    if not inv.window:
        a.text = "This case defines no crime window, so opportunity can't be assessed."
        return a
    lines = [f"Crime window: {inv.window.describe()}."]
    for p, o in inv.opportunity.items():
        if people and p not in people:
            continue
        lines.append(f"- {p}: {o.access.value}. {o.explanation}")
        a.cite("record", *o.evidence)
    a.text = "\n".join(lines)
    return a


def _why(inv, question, people, places, t) -> Answer:
    asm = inv.assessment
    if not people:
        return _culprit(inv, question, people, places, t)
    p = people[0]
    if p not in asm.logs:
        return Answer(question, "why", f"{p} is not a suspect in this case.")
    log = asm.logs[p]
    rank = [l.suspect for l in asm.ranking()].index(p) + 1
    a = Answer(question, "why", "")
    lines = [f"{p} ranks #{rank} of {len(asm.logs)} with a score of {log.score:+.1f}."]
    for s in sorted(log.steps, key=lambda s: -abs(s.weight)):
        if s.weight == 0 and s.label is not Label.SPECULATION:
            continue
        lines.append(f"- {s.weight:+.1f} {s.label.value}: {s.text}")
        kind = {"fact": "record", "claim": "statement"}.get(s.label.value, s.label.value)
        a.cite(kind, *s.evidence)
    a.text = "\n".join(lines)
    return a


def _culprit(inv, question, people, places, t) -> Answer:
    asm = inv.assessment
    level, reasons = asm.confidence_reasons()
    top = asm.ranking()[0]
    a = Answer(question, "culprit", "")
    lines = [f"Most likely: {top.suspect} ({top.score:+.1f}), confidence {level}."] + [f"- {r}" for r in reasons]
    for s in sorted((s for s in top.steps if s.weight > 0), key=lambda s: -s.weight)[:3]:
        lines.append(f"- {s.weight:+.1f} {s.label.value}: {s.text}")
        a.cite({"fact": "record", "claim": "statement"}.get(s.label.value, s.label.value), *s.evidence)
    a.text = "\n".join(lines)
    return a


def _confidence(inv, question, people, places, t) -> Answer:
    level, reasons = inv.assessment.confidence_reasons()
    return Answer(question, "confidence", f"Confidence: {level}.\n" + "\n".join(f"- {r}" for r in reasons))


def _what_happened(inv, question, people, places, t) -> Answer | None:
    if t is None:
        return None
    a = Answer(question, "what_happened", "")
    events = [e for e in inv.timeline.events if abs(e.time - t) <= timedelta(minutes=20)]
    if not events:
        a.text = f"Nothing in the evidence is timed within 20 minutes of {t:%H:%M}."
        return a
    lines = [f"Around {t:%m-%d %H:%M}:"]
    for e in events:
        kind = "record" if e.kind is EvidenceKind.RECORD else "statement"
        lines.append(f"- {e.time:%H:%M} ({kind}) [{e.quote.cite()}]")
        a.cite(kind, e.quote)
    a.text = "\n".join(lines)
    return a


def _search(inv, question: str) -> Answer:
    hits = inv.store.search(question, k=5)
    a = Answer(question, "search", "")
    if not hits:
        a.text = "I couldn't match that question to anything in the evidence. Try naming a person, a place or a time."
        return a
    a.text = ("I don't have a specific rule for that question. These are the most relevant passages; "
              "no conclusion is drawn from them:")
    for h in hits:
        a.cite(_kind_of(inv, h.quote), h.quote)
    return a


_HANDLERS: dict[str, Callable] = {
    "confidence": _confidence, "lie": _lie, "where": _where, "who_at": _who_at, "motive": _motive,
    "alibi": _alibi, "connections": _connections, "contradictions": _contradictions,
    "opportunity": _opportunity, "why": _why, "culprit": _culprit, "what_happened": _what_happened,
}


# --- Optional: LLM-phrased answers -------------------------------------------------------------

# answerer(question, evidence_text, rules_answer_text) -> {"answer": str, "quotes": [{"doc", "text"}]}
Answerer = Callable[[str, str, str], dict]


def answer_with_llm(inv, question: str, answerer: Answerer) -> Answer:
    """Claude writes the answer from retrieved evidence plus the rules answer; its quotes are checked."""
    base = ask(inv, question)
    passages = {q for _, q in base.citations} | {h.quote for h in inv.store.search(question, k=8)}
    evidence = "\n".join(f"[{q.doc_id}] {q.text}" for q in sorted(passages, key=lambda q: (q.doc_id, q.start)))
    reply = answerer(question, evidence, base.render())
    a = Answer(question, base.intent, str(reply.get("answer", "")).strip(), source="llm")
    for item in reply.get("quotes") or []:
        q = find_quote(inv.index.case, item.get("doc", ""), item.get("text", ""))
        if q is None:
            a.rejected.append(f"[{item.get('doc')}] {item.get('text')!r}")
        else:
            a.cite(_kind_of(inv, q), q)
    if not a.text or not a.citations:
        base.rejected = a.rejected
        base.text = "(The LLM answer had no verifiable quotes, so the rules answer is shown.)\n" + base.text
        return base
    return a
