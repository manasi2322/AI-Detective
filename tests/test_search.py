from detective.grounding import verify


def test_search_finds_relevant_clues_not_noise(inv1):
    hits = inv1.store.search("laptop drawer", k=3)
    assert len(hits) == 3
    assert {h.quote.doc_id for h in hits} <= {"interview_daniel", "interview_lena"}
    assert all("drawer" in h.quote.text for h in hits)
    assert not any(h.quote.doc_id == "notice_kitchen" for h in inv1.store.search("laptop drawer", k=10))


def test_search_filters_by_person_and_returns_citable_quotes(case1, inv1):
    hits = inv1.store.search("Daniel prototype laptop", k=10, person="Marcus Hale")
    assert hits
    assert all("Marcus Hale" in p.people for p in inv1.store.passages if p.quote in {h.quote for h in hits})
    assert {"chat_marcus_alex", "interview_marcus"} <= {h.quote.doc_id for h in hits}
    for h in hits:
        assert verify(case1, h.quote)
    # Type filter: only hard records.
    records = inv1.store.search("Marcus Hale Design Lab", doc_types={"badge_log", "cctv"})
    assert records and all(h.doc_type in {"badge_log", "cctv"} for h in records)
