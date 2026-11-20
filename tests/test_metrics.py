from detective.evaluate import _mutate, evaluate_case, grounding_attack

from .conftest import CASE1, CASE3


def test_invented_evidence_is_always_rejected_and_genuine_accepted(inv1, inv2, inv3):
    for inv in (inv1, inv2, inv3):
        r = grounding_attack(inv)
        assert r["invented"] >= 30 and r["invented_rejected"] == r["invented"]
        assert r["genuine"] >= 30 and r["genuine_accepted"] == r["genuine"]


def test_fakes_are_believable_one_detail_changes():
    assert _mutate("2026-03-12 19:41 | Marcus Hale | Main Entrance | ENTRY") == \
        "2026-03-12 19:44 | Marcus Hale | Main Entrance | ENTRY"
    assert _mutate("I didn't come back that night.") == "I never didn't come back that night."


def test_timeline_and_retrieval_metrics():
    for d in (CASE1, CASE3):
        r = evaluate_case(d)
        assert r.metrics["timeline"] == 1.0 and r.metrics["retrieval@5"] == 1.0
        assert r.metrics["invented_rejected"] == 1.0


def test_a_missing_timeline_event_is_a_failed_check(tmp_path):
    import json
    import shutil
    copy = tmp_path / "c1"
    shutil.copytree(CASE1, copy)
    sol = json.loads((copy / "solution.json").read_text())
    sol["timeline"].append({"time": "2026-03-12 23:59", "person": "Marcus Hale", "doc": "badge_log"})
    (copy / "solution.json").write_text(json.dumps(sol))
    r = evaluate_case(copy)
    assert r.metrics["timeline"] < 1.0
    assert not next(c for c in r.checks if "23:59" in c.name).passed
