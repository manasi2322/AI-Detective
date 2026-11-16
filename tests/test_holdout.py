"""A second case written separately from Case 1, with different people, places and wording.

It checks that the alibi, speculation and opportunity rules are not just fitted to Case 1.
"""

from detective.alibi import Verdict
from detective.grounding import verify


def test_holdout_liar_is_the_only_broken_alibi(inv_holdout, holdout_solution):
    broken = {p for p, a in inv_holdout.alibis.items() if a.status == "broken"}
    assert broken == {lie["person"] for lie in holdout_solution["lies"]}
    [c] = inv_holdout.alibis["Tomas Reyes"].contradictions
    assert c.claim.quote.text == holdout_solution["lies"][0]["claim"]
    assert {q.doc_id for q in c.evidence} == set(holdout_solution["lies"][0]["contradicted_by"])


def test_holdout_honest_alibis_hold(inv_holdout, holdout_solution):
    for person in holdout_solution["honest"]:
        alibi = inv_holdout.alibis[person]
        assert alibi.status == "holds", person
        assert all(c.verdict is not Verdict.CONTRADICTED for c in alibi.checks)


def test_holdout_speculation_is_flagged(inv_holdout, holdout_solution):
    flagged = {(s.speaker, a) for s in inv_holdout.speculation for a in s.about}
    assert flagged == {(x["speaker"], x["about"]) for x in holdout_solution["speculation"]}


def test_holdout_opportunity_matches_answer_key(inv_holdout, holdout_solution):
    for level, people in holdout_solution["opportunity"].items():
        for person in people:
            assert inv_holdout.opportunity[person].access.value == level, person


def test_holdout_everything_is_grounded(inv_holdout):
    assert all(verify(inv_holdout.index.case, q) for q in inv_holdout.all_quotes())
