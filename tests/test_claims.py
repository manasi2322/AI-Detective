from datetime import datetime

from detective.claims import HOME, ClaimType
from detective.grounding import verify


def _claims(inv, person, ctype=None):
    return [c for c in inv.claims if c.person == person and (ctype is None or c.type is ctype)]


def test_marcus_departure_and_no_return_are_parsed(inv1):
    [dep] = _claims(inv1, "Marcus Hale", ClaimType.DEPARTURE)
    assert dep.start == datetime(2026, 3, 12, 18, 0)
    [nr] = _claims(inv1, "Marcus Hale", ClaimType.NO_RETURN)
    # "I didn't come back that night" has no time: it runs from his stated departure to the next morning.
    assert nr.quote.text == "I didn't come back that night."
    assert nr.start == dep.start and nr.end == datetime(2026, 3, 13, 6, 0)


def test_off_site_ranges_become_elsewhere_claims(inv1):
    [priya] = _claims(inv1, "Priya Nair", ClaimType.ELSEWHERE)
    assert priya.location == "Lantern Bistro" and priya.approximate
    assert (priya.start, priya.end) == (datetime(2026, 3, 12, 19, 0), datetime(2026, 3, 12, 21, 30))
    [sam] = _claims(inv1, "Sam Whitfield", ClaimType.ELSEWHERE)
    assert sam.location == HOME and sam.end == datetime(2026, 3, 12, 20, 0)


def test_only_first_person_statements_by_the_speaker_are_claims(inv1):
    assert {c.quote.doc_id for c in inv1.claims} <= {d for d in inv1.index.case.documents if d.startswith("interview_")}
    texts = {c.quote.text for c in inv1.claims}
    # Questions, chat lines about others, records and the email are not whereabouts claims.
    assert not any(t.endswith("?") for t in texts)
    assert not any("He keeps it locked in the lab" in t for t in texts)
    assert len(inv1.claims) == 12


def test_every_claim_is_grounded(inv1, inv_holdout):
    for inv in (inv1, inv_holdout):
        for c in inv.claims:
            assert verify(inv.index.case, c.quote), c.id
