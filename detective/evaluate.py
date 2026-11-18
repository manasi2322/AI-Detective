"""Evaluation: run every case and score the results against its answer key (solution.json).

Only the evaluator and the tests read solution.json; the investigation never does. Each answer
key lists what it knows (culprit, lies, honest people, disputed records, ...), and every listed
item becomes one pass/fail check. A case's score is the share of its checks that pass.

    python -m detective evaluate            # all cases in ./cases
    python evaluate.py                      # same, from the repo root
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .alibi import Verdict
from .loader import case_stages, load_case, load_solution
from .pipeline import investigate
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

    report = build_report(inv, earlier)
    check = check_citations(case, report)
    add(Check("every report citation matches its source", check.ok and check.quoted > 0,
              f"{check.quoted} quoted, {check.references} references" + (f"; {check.problems}" if check.problems else "")))
    return res


def evaluate_all(cases_dir: str | Path = "cases") -> list[CaseResult]:
    dirs = sorted(p for p in Path(cases_dir).iterdir() if (p / "solution.json").exists())
    return [evaluate_case(d) for d in dirs]


def render(results: list[CaseResult], verbose: bool = False) -> str:
    out = ["| Case | Difficulty | Named | Expected | Confidence | Checks passed | Score |",
           "|---|---|---|---|---|---|---|"]
    for r in results:
        passed = sum(c.passed for c in r.checks)
        out.append(f"| {r.title} | {r.difficulty} | {r.named} | {r.expected} | {r.confidence} | "
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
