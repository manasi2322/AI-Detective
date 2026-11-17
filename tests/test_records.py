from datetime import datetime

from detective.opportunity import Access


def test_case1_has_no_disputed_records(inv1):
    # Every badge line in Case 1 agrees with CCTV (same door, or no camera nearby).
    assert inv1.disputes == []


def test_badge_disputed_by_cctv_is_excluded(inv_disputed):
    [d] = inv_disputed.disputes
    assert d.person == "Nora Quint" and d.record.cite() == "badge:L3" and d.cctv.cite() == "cctv:L1"
    # The disputed swipe is not used: Nora is not placed in the Server Room, and her canteen alibi holds.
    assert d.record not in {m.quote for m in inv_disputed.presence.movements("Nora Quint")}
    assert inv_disputed.opportunity["Nora Quint"].access is Access.ON_SITE
    assert inv_disputed.alibis["Nora Quint"].status == "holds"
    assert not inv_disputed.presence.between("Nora Quint", datetime(2026, 6, 1, 21, 0),
                                              datetime(2026, 6, 1, 21, 5), location="Server Room")
