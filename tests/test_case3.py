"""Case 3, "The Leaked Formula": the first evidence points to the wrong person."""

from detective.alibi import Verdict
from detective.loader import case_stages, load_case
from detective.opportunity import Access

from .conftest import CASE3


def test_early_evidence_points_to_the_wrong_person(inv3_stage1, solution3):
    a = inv3_stage1.assessment
    assert a.most_likely == solution3["initial_suspect"] != solution3["culprit"]
    assert inv3_stage1.opportunity["Iris Kemp"].access is Access.AT_SCENE  # her login, at stage 1


def test_full_evidence_points_to_the_culprit(inv3, solution3):
    a = inv3.assessment
    assert a.most_likely == solution3["culprit"]
    level, why = a.confidence()
    assert level == "medium" and "statements add" in why
    assert all(log.score < 0 for log in a.ranking()[1:])


def test_login_disputed_only_once_cctv_is_uncovered(inv3, inv3_stage1):
    assert inv3_stage1.disputes == []
    assert [d.record.cite() for d in inv3.disputes] == ["login_log:L1"]
    assert inv3.opportunity["Iris Kemp"].access is Access.ON_SITE


def test_door_exit_then_car_park_sighting_is_not_a_dispute(inv3):
    # Badged out of the main door at 22:18, on the car park camera at 22:19: one trip, no conflict.
    assert "badge_log:L5" not in {d.record.cite() for d in inv3.disputes}
    assert inv3.alibis["Iris Kemp"].status == "holds"


def test_evidence_stages_are_loaded_in_order():
    assert case_stages(CASE3) == [1, 2]
    early, full = load_case(CASE3, stage=1), load_case(CASE3)
    assert set(full.documents) - set(early.documents) == {"cctv", "chat_noah_rhea"}


def test_culprit_with_a_true_alibi_is_caught_by_the_denial(inv3):
    noah = inv3.alibis["Noah Fisk"]
    assert noah.status == "holds" and all(c.verdict is Verdict.SUPPORTED for c in noah.checks)
    [c] = inv3.connections
    assert c.suspect == "Noah Fisk" and c.denial.text == "I've never spoken to anyone at Veltrix."
