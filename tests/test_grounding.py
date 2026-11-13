from dataclasses import replace

from detective.grounding import find_quote, verify


def test_every_extracted_finding_is_an_exact_quote(case1, inv1):
    assert inv1.index.events
    for event in inv1.index.events:
        assert verify(case1, event.quote), event.id
    for mentions in inv1.index.mentions.values():
        for m in mentions:
            assert verify(case1, m.quote)


def test_fabricated_quote_cannot_be_grounded(case1):
    assert find_quote(case1, "interview_marcus", "I came back at 7:40 PM to grab my charger.") is None
    assert find_quote(case1, "no_such_doc", "Marcus Hale") is None
    assert find_quote(case1, "badge_log", "   ") is None
    real = find_quote(case1, "interview_marcus", "I didn't come back that night.")
    assert real is not None and real.line == 2


def test_tampered_quote_fails_verification(case1):
    q = find_quote(case1, "badge_log", "2026-03-12 19:44 | Marcus Hale | Design Lab | ENTRY")
    assert verify(case1, q)
    assert not verify(case1, replace(q, text=q.text.replace("19:44", "21:44")))
    assert not verify(case1, replace(q, start=q.start + 1, end=q.end + 1))
