from datetime import date

from detective.models import EvidenceKind


def test_loads_every_document(case1):
    assert len(case1.documents) == 11
    assert {"badge_log", "cctv_summary", "interview_marcus", "chat_marcus_alex", "notice_kitchen"} <= set(case1.documents)


def test_front_matter_sets_type_date_and_reliability(case1):
    badge = case1.documents["badge_log"]
    interview = case1.documents["interview_marcus"]
    assert badge.type == "badge_log" and badge.kind is EvidenceKind.RECORD
    assert interview.author == "Marcus Hale" and interview.kind is EvidenceKind.CLAIM
    assert interview.date == date(2026, 3, 12)
    assert not badge.body.startswith("---")


def test_solution_names_one_of_four_suspects(case1, solution1):
    suspects = {p.name for p in case1.suspects}
    assert len(suspects) == 4
    assert solution1["culprit"] in suspects
    for item in solution1["key_evidence"]:
        assert item["doc"] in case1.documents
