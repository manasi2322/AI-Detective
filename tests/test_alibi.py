from dataclasses import replace
from datetime import datetime

from detective.alibi import AlibiChecker, Verdict
from detective.claims import ClaimType


def _check(inv, person, ctype):
    [c] = [c for c in inv.alibis[person].checks if c.claim.type is ctype]
    return c


def test_marcus_no_return_is_contradicted_with_quotes_from_both_sides(inv1):
    c = _check(inv1, "Marcus Hale", ClaimType.NO_RETURN)
    assert c.verdict is Verdict.CONTRADICTED
    assert c.claim.quote.cite() == "interview_marcus:L2"
    assert [q.cite() for q in c.evidence] == ["badge_log:L6", "badge_log:L7"]
    assert "19:41" in c.explanation and "19:44" in c.explanation


def test_true_part_of_a_lie_is_still_supported(inv1):
    # Marcus really did leave at ~18:00; only "didn't come back" is false.
    c = _check(inv1, "Marcus Hale", ClaimType.DEPARTURE)
    assert c.verdict is Verdict.SUPPORTED and [q.cite() for q in c.evidence] == ["badge_log:L2"]


def test_only_the_liar_has_a_broken_alibi(inv1, solution1):
    broken = {p for p, a in inv1.alibis.items() if a.status == "broken"}
    assert broken == {lie["person"] for lie in solution1["lies"]}
    for person in solution1["honest"]:
        assert inv1.alibis[person].status == "holds", person
        assert not inv1.alibis[person].contradictions


def test_lena_arrival_is_confirmed_by_badge_log_and_cctv(inv1):
    c = _check(inv1, "Lena Torres", ClaimType.ARRIVAL)
    assert c.verdict is Verdict.SUPPORTED
    assert {q.doc_id for q in c.evidence} == {"badge_log", "cctv_summary"}


def test_unconfirmable_alibi_is_consistent_not_supported(inv1):
    # No badge reader at the restaurant: the records cannot prove the dinner, only fail to refute it.
    c = _check(inv1, "Priya Nair", ClaimType.ELSEWHERE)
    assert c.verdict is Verdict.CONSISTENT
    assert c.assumptions and "cannot confirm" in c.explanation


def test_unidentified_cctv_figure_is_never_used_against_anyone(inv1):
    for alibi in inv1.alibis.values():
        for c in alibi.checks:
            assert all(not (q.doc_id == "cctv_summary" and q.line in (1, 2)) for q in c.evidence)


def test_victim_statements_are_checked_too(inv1):
    assert inv1.alibis["Daniel Okafor"].status == "holds"
    assert all(c.verdict is Verdict.SUPPORTED for c in inv1.alibis["Daniel Okafor"].checks)


def test_a_wrong_departure_time_is_caught(inv1):
    # Same quote, but pretend Sam said 7:30 PM: the 18:40 exit now contradicts it.
    real = _check(inv1, "Sam Whitfield", ClaimType.DEPARTURE).claim
    fake = replace(real, start=datetime(2026, 3, 12, 19, 30))
    check = AlibiChecker(inv1.index.case, inv1.presence).check(fake)
    assert check.verdict is Verdict.CONTRADICTED and "50 minutes off" in check.explanation
