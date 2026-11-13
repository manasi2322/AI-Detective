from datetime import datetime

from detective.models import EvidenceKind


def _find(events, doc_id, time):
    return [e for e in events if e.doc_id == doc_id and e.time == time]


def test_timeline_is_chronological(inv1):
    times = [e.time for e in inv1.timeline.events]
    assert times == sorted(times)
    assert len(inv1.timeline.events) == len(inv1.index.events)


def test_records_and_claims_are_separated(inv1):
    tl = inv1.timeline
    assert {e.doc_id for e in tl.records()} == {"badge_log", "cctv_summary", "case_brief"}
    assert all(e.kind is EvidenceKind.CLAIM for e in tl.claims())
    assert {"interview_marcus", "interview_priya", "chat_marcus_alex"} <= {e.doc_id for e in tl.claims()}
    assert len(tl.records()) + len(tl.claims()) == len(tl.events)


def test_badge_log_shows_marcus_entering_design_lab(inv1):
    [e] = _find(inv1.timeline.events, "badge_log", datetime(2026, 3, 12, 19, 44))
    assert e.kind is EvidenceKind.RECORD
    assert e.actor == "Marcus Hale" and e.location == "Design Lab"
    assert e.quote.cite() == "badge_log:L7"


def test_marcus_alibi_is_recorded_as_a_claim(inv1):
    [e] = _find(inv1.timeline.events, "interview_marcus", datetime(2026, 3, 12, 18, 0))
    assert e.kind is EvidenceKind.CLAIM
    assert e.actor == "Marcus Hale"
    assert "left the office at 6 PM" in e.quote.text


def test_interviewer_questions_are_not_events(inv1):
    for e in inv1.index.events:
        assert not e.quote.text.endswith("?") or e.doc_id == "email_sam_daniel"
    assert not _find(inv1.index.events, "interview_marcus", datetime(2026, 3, 12, 0, 0))


def test_unidentified_cctv_figure_is_not_guessed(inv1):
    [e] = _find(inv1.timeline.events, "cctv_summary", datetime(2026, 3, 12, 19, 58))
    assert e.actor is None and e.people == ()
    assert e.location == "Parking Garage"
