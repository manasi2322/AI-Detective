from dataclasses import replace

import pytest

from detective.investigator import Label, assess, validate
from detective.models import EvidenceKind
from detective.pipeline import investigate


def _steps(inv):
    return [s for log in inv.assessment.logs.values() for s in log.steps]


def test_every_step_is_labelled_cited_and_grounded(inv1, inv_holdout):
    for inv in (inv1, inv_holdout):
        for s in _steps(inv):
            assert isinstance(s.label, Label) and s.evidence and s.text
            assert validate(inv.index.case, s) is None


def test_facts_come_only_from_records(inv1, inv_holdout):
    for inv in (inv1, inv_holdout):
        facts = [s for s in _steps(inv) if s.label is Label.FACT]
        assert facts
        for s in facts:
            assert all(inv.index.case.documents[q.doc_id].kind is EvidenceKind.RECORD for q in s.evidence)


def test_speculation_never_changes_a_score(inv1):
    spec = [s for s in _steps(inv1) if s.label is Label.SPECULATION]
    assert spec and all(s.weight == 0 for s in spec)
    without = assess(inv1.index.case, inv1.alibis, inv1.opportunity, inv1.window, inv1.motives,
                     inv1.cctv_matches, inv1.connections, [], inv1.disputes)
    assert {n: l.score for n, l in without.logs.items()} == {n: l.score for n, l in inv1.assessment.logs.items()}


@pytest.mark.parametrize("which", ["case1", "holdout"])
def test_evidence_favours_the_culprit(which, inv1, inv_holdout, solution1, holdout_solution):
    inv, sol = (inv1, solution1) if which == "case1" else (inv_holdout, holdout_solution)
    a = inv.assessment
    assert a.most_likely == sol["culprit"]
    ranked = a.ranking()
    assert ranked[0].score >= ranked[1].score + 5
    assert all(log.score < 0 for log in ranked[1:])
    assert a.confidence()[0] == "high"


def test_rules_reject_a_fact_that_cites_a_statement(inv1):
    fact = next(s for s in _steps(inv1) if s.label is Label.FACT)
    bad = replace(fact, evidence=(fact.tested or inv1.claims[0].quote,))
    assert validate(inv1.index.case, bad) == "a fact may only cite records (badge log, login log, CCTV, brief)"


def fake_investigator(case, assessment):
    """Stands in for Claude: one grounded step and four that break the rules."""
    return [
        {"suspect": "Marcus Hale", "label": "claim", "weight": 1.0, "reasoning": "Agreed to the handover time.",
         "quotes": [{"doc": "chat_marcus_alex", "text": "Thursday evening works. Bring whatever you can."}]},
        {"suspect": "Lena Torres", "label": "fact", "weight": 2.0, "reasoning": "Invented sighting.",
         "quotes": [{"doc": "cctv_summary", "text": "Lena Torres carries a laptop out of the lab."}]},
        {"suspect": "Lena Torres", "label": "fact", "weight": 1.0, "reasoning": "Priya says so.",
         "quotes": [{"doc": "interview_priya", "text": "Honestly, it was probably Lena."}]},
        {"suspect": "Lena Torres", "label": "speculation", "weight": 1.0, "reasoning": "Cleaners are always there.",
         "quotes": [{"doc": "interview_priya", "text": "The cleaners are in that lab every night."}]},
        {"suspect": "Alex Brandt", "label": "claim", "weight": 1.0, "reasoning": "Not a suspect.",
         "quotes": [{"doc": "chat_marcus_alex", "text": "Thursday evening works."}]},
    ]


def test_llm_steps_follow_the_same_rules(case1, inv1):
    inv = investigate(case1, investigator=fake_investigator)
    assert sorted(r.reason for r in inv.assessment.rejections) == [
        "a fact may only cite records (badge log, login log, CCTV, brief)",
        "quote not found verbatim in the documents",
        "speculation must weigh zero",
        "unknown suspect 'Alex Brandt'",
    ]
    llm = [s for s in _steps(inv) if s.source == "llm"]
    assert len(llm) == 1 and llm[0].suspect == "Marcus Hale"
    assert inv.assessment.logs["Marcus Hale"].score == inv1.assessment.logs["Marcus Hale"].score + 1
    assert inv.assessment.logs["Lena Torres"].score == inv1.assessment.logs["Lena Torres"].score
