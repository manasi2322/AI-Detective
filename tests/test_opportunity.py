from dataclasses import replace
from datetime import datetime

import pytest

from detective.opportunity import Access, UngroundedWindow, resolve_window


def test_window_is_read_from_quoted_evidence(inv1):
    w = inv1.window
    assert (w.start, w.end) == (datetime(2026, 3, 12, 18, 15), datetime(2026, 3, 13, 8, 50))
    assert (w.start_quote.cite(), w.end_quote.cite()) == ("interview_daniel:L2", "case_brief:L1")


def test_access_levels_match_the_answer_key(inv1, solution1):
    for level, people in solution1["opportunity"].items():
        for person in people:
            assert inv1.opportunity[person].access.value == level, person


def test_at_scene_cites_the_scene_records(inv1):
    assert [q.cite() for q in inv1.opportunity["Marcus Hale"].evidence] == ["badge_log:L7"]
    assert [q.cite() for q in inv1.opportunity["Lena Torres"].evidence] == ["badge_log:L9"]


def test_on_site_without_scene_access_is_kept_apart(inv1):
    sam = inv1.opportunity["Sam Whitfield"]
    assert sam.access is Access.ON_SITE and "18:40" in sam.explanation and sam.assumptions


def test_invented_window_quote_is_rejected(case1):
    bad = dict(case1.window, start={"doc": "interview_daniel", "quote": "At 5 PM I hid the laptop."})
    with pytest.raises(UngroundedWindow):
        resolve_window(replace(case1, window=bad))


def test_marcus_open_ended_stay(inv1):
    [stay] = [s for s in inv1.presence.stays("Marcus Hale") if s.start == datetime(2026, 3, 12, 19, 41)]
    assert stay.end is None and "no exit recorded" in stay.describe()
