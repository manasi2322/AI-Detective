"""Case 2, "The Gallery Switch": a friend's "perfect" alibi and the guard's badge used by someone else."""

from detective.alibi import Verdict
from detective.claims import ClaimType
from detective.investigator import Label
from detective.opportunity import Access


def test_culprit_named_with_high_confidence(inv2, solution2):
    a = inv2.assessment
    assert a.most_likely == solution2["culprit"] and a.confidence()[0] == "high"
    assert all(log.score < 0 for log in a.ranking()[1:])


def test_friends_alibi_is_a_vouch_not_the_suspects_own_account(inv2):
    [c] = [c for c in inv2.alibis["Victor Lane"].checks if c.claim.kind == "vouch"]
    assert c.claim.reported_by == "Celia Ward" and c.claim.type is ClaimType.ELSEWHERE
    assert c.claim.location == "Celia's flat"
    assert c.claim.quote.text == "Victor was with me at my flat from 8 PM until midnight."


def test_perfect_alibi_falls_to_the_wifi_record(inv2):
    for c in inv2.alibis["Victor Lane"].checks:
        if c.claim.type is ClaimType.ELSEWHERE:
            assert c.verdict is Verdict.CONTRADICTED
            assert [q.cite() for q in c.evidence][0] == "wifi_log:L1"
    vouch = [s for s in inv2.assessment.logs["Victor Lane"].steps if "Alibi from Celia Ward" in s.text]
    assert len(vouch) == 1 and vouch[0].label is Label.FACT


def test_guards_badge_used_by_someone_else_is_excluded(inv2):
    [d] = inv2.disputes
    assert d.person == "Omar Haddad" and d.record.cite() == "badge_log:L7"
    assert inv2.opportunity["Omar Haddad"].access is Access.ON_SITE
    assert inv2.alibis["Omar Haddad"].status == "holds"


def test_conflicting_statements_are_resolved_by_records(inv2):
    assert len(inv2.conflicts) == 2  # Victor's own account and Celia's both clash with Ben's sighting
    for c in inv2.conflicts:
        assert c.person == "Victor Lane" and c.backed is not None
        assert c.backed.claim.reported_by == "Ben Price" and c.backed.verdict is Verdict.SUPPORTED


def test_misleading_evidence_against_the_guard_is_outweighed(inv2):
    omar = inv2.assessment.logs["Omar Haddad"]
    kinds = {s.kind for s in omar.steps}
    assert {"dispute", "speculation", "motive"} <= kinds  # badge, Lucy's guess, money complaints
    assert omar.score < 0 < inv2.assessment.logs["Victor Lane"].score


def test_side_door_figure_matched_to_victor_as_assumption(inv2):
    first = inv2.cctv_matches[0]
    assert first.person == "Victor Lane" and first.label == "assumption"
    assert [q.cite() for q in first.records] == ["wifi_log:L1"]  # the disputed badge is not a candidate
