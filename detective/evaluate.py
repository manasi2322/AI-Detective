"""Evaluation: run every case and score the results against its answer key (solution.json).

Only the evaluator and the tests read solution.json; the investigation never does. Each answer
key lists what it knows (culprit, lies, honest people, disputed records, ...), and every listed
item becomes one pass/fail check. A case's score is the share of its checks that pass.

    python -m detective evaluate            # all cases in ./cases
    python evaluate.py                      # same, from the repo root
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .alibi import Verdict
from .investigator import add_llm_steps
from .llm_extract import LLMEventExtractor
from .loader import case_stages, load_case, load_solution
from .pipeline import investigate
from .qa import answer_with_llm
from .report import build_report, check_citations


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    case_id: str
    title: str
    difficulty: str
    named: str
    expected: str
    confidence: str
    checks: list[Check] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    @property
    def score(self) -> float:
        return sum(c.passed for c in self.checks) / len(self.checks) if self.checks else 0.0

    @property
    def solved(self) -> bool:
        return self.named == self.expected


def _same(name: str, found, expected) -> Check:
    found, expected = set(found), set(expected)
    detail = "" if found == expected else f"found {sorted(found)}, expected {sorted(expected)}"
    return Check(name, found == expected, detail)


def evaluate_case(case_dir: str | Path) -> CaseResult:
    case = load_case(case_dir)
    sol = load_solution(case_dir)
    inv = investigate(case)
    a = inv.assessment
    level = a.confidence()[0]
    res = CaseResult(case.id, case.title, case.difficulty, a.most_likely, sol["culprit"], level)
    add = res.checks.append

    add(Check("names the culprit", a.most_likely == sol["culprit"], f"named {a.most_likely}"))
    add(Check("confidence is not low", level != "low", f"confidence {level}"))

    stages = case_stages(case_dir)
    earlier = None
    if "initial_suspect" in sol and len(stages) > 1:
        earlier = investigate(load_case(case_dir, stage=stages[0]))
        first = earlier.assessment.most_likely
        add(Check("early evidence points to the expected wrong lead", first == sol["initial_suspect"],
                  f"stage {stages[0]} named {first}"))

    all_checks = [c for al in inv.alibis.values() for c in al.checks]
    for lie in sol.get("lies", []):
        caught = any(
            c.verdict is Verdict.CONTRADICTED and lie["claim"] in c.claim.quote.text
            and lie["person"] in (c.claim.person if not c.claim.reported_by else c.claim.reported_by,)
            and {q.doc_id for q in c.evidence} & set(lie["contradicted_by"])
            for c in all_checks
        ) or any(
            c.denial is not None and c.suspect == lie["person"] and lie["claim"] in c.denial.text
            and {q.doc_id for q in c.messages} & set(lie["contradicted_by"])
            for c in inv.connections
        )
        add(Check(f"catches lie by {lie['person']}: “{lie['claim']}”", caught))

    for person in sol.get("honest", []):
        status = inv.alibis[person].status
        add(Check(f"{person}'s alibi is not broken", status != "broken", f"status {status}"))

    culprit_score = a.logs[sol["culprit"]].score
    for rh in sol.get("red_herrings", []):
        if "person" in rh and rh["person"] in a.logs:
            s = a.logs[rh["person"]].score
            add(Check(f"red herring {rh['person']} scores below the culprit", s < culprit_score, f"{s:+.1f}"))

    if "disputed" in sol:
        add(_same("disputed records", (d.record.cite() for d in inv.disputes), sol["disputed"]))
    for sc in sol.get("statement_conflicts", []):
        ok = any(c.person == sc["person"] and c.backed is not None
                 and (c.backed.claim.reported_by or c.backed.claim.person) == sc["backed"] for c in inv.conflicts)
        add(Check(f"statement conflict about {sc['person']} resolved in favour of {sc['backed']}", ok))
    if "speculation" in sol:
        add(_same("speculation flagged", ((s.speaker, x) for s in inv.speculation for x in s.about),
                  ((x["speaker"], x["about"]) for x in sol["speculation"])))
    for person, types in sol.get("motives", {}).items():
        add(_same(f"motives of {person}", {m.type.value for m in inv.motives if m.person == person}, types))
    if "cctv_matches" in sol:
        add(_same("CCTV matches", ((m.cctv.cite(), m.person) for m in inv.cctv_matches),
                  ((x["cctv"], x["person"]) for x in sol["cctv_matches"])))
    if "connections" in sol:
        add(_same("hidden connections", ((c.suspect, c.party, c.denial is not None) for c in inv.connections),
                  ((x["suspect"], x["party"], x["denied"]) for x in sol["connections"])))
    for level_name, people in sol.get("opportunity", {}).items():
        for person in people:
            got = inv.opportunity[person].access.value
            add(Check(f"opportunity of {person} is '{level_name}'", got == level_name, f"got '{got}'"))

    if "timeline" in sol:
        found = 0
        for want in sol["timeline"]:
            ok = _has_event(inv, want)
            found += ok
            who = want["person"] or "unidentified person"
            add(Check(f"timeline has {want['time']} {who} [{want['doc']}]", ok))
        res.metrics["timeline"] = found / len(sol["timeline"])
    if "key_evidence" in sol:
        hit = 0
        for k in sol["key_evidence"]:
            docs = [h.quote.doc_id for h in inv.store.search(k["fact"], k=5)]
            ok = k["doc"] in docs
            hit += ok
            add(Check(f"search finds {k['doc']} in the top 5 for “{k['fact']}”", ok, f"top 5: {docs}"))
        res.metrics["retrieval@5"] = hit / len(sol["key_evidence"])

    attack = grounding_attack(inv)
    res.metrics["invented_rejected"] = attack["invented_rejected"] / attack["invented"]
    res.metrics["genuine_accepted"] = attack["genuine_accepted"] / attack["genuine"]
    add(Check("every invented item is rejected", attack["invented_rejected"] == attack["invented"],
              f"{attack['invented_rejected']}/{attack['invented']}"))
    add(Check("every genuine item is accepted", attack["genuine_accepted"] == attack["genuine"],
              f"{attack['genuine_accepted']}/{attack['genuine']}"))

    report = build_report(inv, earlier)
    check = check_citations(case, report)
    add(Check("every report citation matches its source", check.ok and check.quoted > 0,
              f"{check.quoted} quoted, {check.references} references" + (f"; {check.problems}" if check.problems else "")))
    return res


def _has_event(inv, want: dict) -> bool:
    t = datetime.strptime(want["time"], "%Y-%m-%d %H:%M")
    for e in inv.timeline.events:
        if e.doc_id != want["doc"] or e.time != t:
            continue
        if want.get("location") and e.location != want["location"]:
            continue
        if want["person"] is None:
            if e.actor is None and not e.people:
                return True
        elif want["person"] == e.actor or want["person"] in e.people:
            return True
    return False


def _mutate(text: str) -> str:
    """A believable fake: the same line with one detail changed (the clock time, or a word)."""
    m = re.search(r"\b\d{1,2}:(\d)(\d)\b", text)
    if m:  # 19:41 -> 19:44: a time that is plausible but not what the document says
        i = m.start(2)
        return text[:i] + str((int(text[i]) + 3) % 10) + text[i + 1:]
    for i, ch in enumerate(text):
        if ch.isdigit():
            return text[:i] + str((int(ch) + 3) % 10) + text[i + 1:]
    words = text.split(" ")
    return " ".join(words[:1] + ["never"] + words[1:])


def grounding_attack(inv) -> dict:
    """Feed invented evidence through every LLM entry point and count how much gets in.

    For each record line and statement, a genuine proposal (real quote) and an invented one (the
    same quote with one detail changed) go through the event extractor, the investigator and the
    follow-up answerer. Invented ones must all be rejected; genuine ones must all be accepted.
    Also tries two rule-breaking steps per case: a FACT citing a statement, and weighted speculation.
    """
    case = inv.index.case
    counts = {"invented": 0, "invented_rejected": 0, "genuine": 0, "genuine_accepted": 0}
    suspect = case.suspects[0].name
    events = [e for e in inv.index.events if e.source == "rules"][:12]

    for e in events:
        doc = case.documents[e.doc_id]
        for genuine, text in ((True, e.quote.text), (False, _mutate(e.quote.text))):
            item = {"quote": text, "time": e.time.isoformat(timespec="minutes"), "actor": e.actor,
                    "location": e.location, "approximate": e.approximate}
            out = LLMEventExtractor.validate(case, doc, item, inv.matcher, "attack")
            accepted = not hasattr(out, "reason")
            _count(counts, genuine, accepted)

    steps = []
    for e in events:
        label = "fact" if doc_kind(case, e.doc_id) == "record" else "claim"
        steps.append((True, {"suspect": suspect, "label": label, "weight": 0.5, "reasoning": "genuine",
                             "quotes": [{"doc": e.doc_id, "text": e.quote.text}]}))
        steps.append((False, {"suspect": suspect, "label": label, "weight": 0.5, "reasoning": "invented",
                              "quotes": [{"doc": e.doc_id, "text": _mutate(e.quote.text)}]}))
    statement = next((e for e in events if doc_kind(case, e.doc_id) != "record"), None)
    if statement is not None:
        steps.append((False, {"suspect": suspect, "label": "fact", "weight": 1, "reasoning": "fact from a statement",
                              "quotes": [{"doc": statement.doc_id, "text": statement.quote.text}]}))
        steps.append((False, {"suspect": suspect, "label": "speculation", "weight": 1, "reasoning": "weighted guess",
                              "quotes": [{"doc": statement.doc_id, "text": statement.quote.text}]}))
    for genuine, item in steps:
        trial = copy.deepcopy(inv.assessment)
        add_llm_steps(case, trial, lambda c, a, item=item: [item])
        _count(counts, genuine, not trial.rejections)

    for e in events[:6]:
        for genuine, text in ((True, e.quote.text), (False, _mutate(e.quote.text))):
            reply = {"answer": "test", "quotes": [{"doc": e.doc_id, "text": text}]}
            a = answer_with_llm(inv, "What happened?", lambda *_, reply=reply: reply)
            _count(counts, genuine, a.source == "llm" and not a.rejected)
    return counts


def _count(counts: dict, genuine: bool, accepted: bool) -> None:
    key = "genuine" if genuine else "invented"
    counts[key] += 1
    if genuine and accepted:
        counts["genuine_accepted"] += 1
    if not genuine and not accepted:
        counts["invented_rejected"] += 1


def doc_kind(case, doc_id: str) -> str:
    return case.documents[doc_id].kind.value


def evaluate_all(cases_dir: str | Path = "cases") -> list[CaseResult]:
    dirs = sorted(p for p in Path(cases_dir).iterdir() if (p / "solution.json").exists())
    return [evaluate_case(d) for d in dirs]


def render(results: list[CaseResult], verbose: bool = False) -> str:
    def pct(r, key):
        return f"{r.metrics[key]:.0%}" if key in r.metrics else "-"

    out = ["| Case | Difficulty | Named | Expected | Confidence | Timeline | Retrieval@5 | Invented rejected "
           "| Checks passed | Score |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        passed = sum(c.passed for c in r.checks)
        out.append(f"| {r.title} | {r.difficulty} | {r.named} | {r.expected} | {r.confidence} | "
                   f"{pct(r, 'timeline')} | {pct(r, 'retrieval@5')} | {pct(r, 'invented_rejected')} | "
                   f"{passed}/{len(r.checks)} | {r.score:.0%} |")
    total = sum(len(r.checks) for r in results)
    passed = sum(c.passed for r in results for c in r.checks)
    solved = sum(r.solved for r in results)
    out += ["", f"Culprit named correctly in {solved}/{len(results)} cases; "
            f"{passed}/{total} checks passed ({passed / total:.0%})." if total else "No cases found."]
    for r in results:
        failed = [c for c in r.checks if not c.passed]
        if verbose or failed:
            out += ["", f"{r.title}:"]
            for c in (r.checks if verbose else failed):
                out.append(f"  [{'PASS' if c.passed else 'FAIL'}] {c.name}" + (f" ({c.detail})" if c.detail else ""))
    return "\n".join(out)
