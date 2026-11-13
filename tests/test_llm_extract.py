from detective.models import EvidenceKind
from detective.pipeline import investigate


def fake_llm(doc, people, places):
    """Stands in for Claude: one correct proposal plus four kinds of hallucination."""
    if doc.id != "interview_marcus":
        return []
    return [
        # Correct and grounded.
        {"quote": "I left the office at 6 PM and went straight home.", "time": "2026-03-12T18:00",
         "actor": "Marcus Hale", "location": "Brightwave Office", "approximate": False},
        # Invented quote.
        {"quote": "I came back at 7:40 PM for my charger.", "time": "2026-03-12T19:40",
         "actor": "Marcus Hale", "location": None, "approximate": False},
        # Real quote, wrong time.
        {"quote": "I left the office at 6 PM and went straight home.", "time": "2026-03-12T19:00",
         "actor": "Marcus Hale", "location": None, "approximate": False},
        # Real quote, unknown person.
        {"quote": "I left the office at 6 PM and went straight home.", "time": "2026-03-12T18:00",
         "actor": "The Janitor", "location": None, "approximate": False},
        # Real quote with no time in it.
        {"quote": "I didn't come back that night.", "time": "2026-03-12T23:00",
         "actor": "Marcus Hale", "location": None, "approximate": False},
    ]


def test_llm_proposals_are_grounded_or_rejected(case1):
    inv = investigate(case1, propose=fake_llm)
    reasons = sorted(r.reason for r in inv.index.rejections)
    assert reasons == [
        "quote does not state any time",
        "quote not found verbatim in source document",
        "time is not the one stated in the quote",
        "unknown person 'The Janitor'",
    ]
    # The valid proposal duplicates a rule-based event, so it is merged, not added twice.
    assert len(inv.index.events) == len(investigate(case1).index.events)
    assert not any("charger" in e.quote.text for e in inv.index.events)
    accepted = [e for e in inv.timeline.events if e.doc_id == "interview_marcus"]
    assert len(accepted) == 1 and accepted[0].kind is EvidenceKind.CLAIM
