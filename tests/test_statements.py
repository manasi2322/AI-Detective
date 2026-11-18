from datetime import datetime

from detective.presence import Presence


def test_one_persons_own_account_is_not_a_conflict(inv1, inv_holdout, inv3):
    assert inv1.conflicts == [] and inv_holdout.conflicts == [] and inv3.conflicts == []


def test_door_sighting_without_direction_counts_as_on_site(inv2):
    # The Wi-Fi log says where Victor's phone was, not which way he went: he was still on site.
    presence: Presence = inv2.presence
    assert presence.state_at("Victor Lane", datetime(2026, 9, 18, 21, 4))[0] == "on site"
