def test_suspects_and_victim_are_found(inv1):
    for name in ["Daniel Okafor", "Marcus Hale", "Priya Nair", "Lena Torres", "Sam Whitfield"]:
        assert inv1.index.mentions[name], name


def test_aliases_resolve_to_canonical_names(inv1):
    marcus_docs = {m.quote.doc_id for m in inv1.index.mentions["Marcus Hale"]}
    # Priya only ever says "Marcus", never the full name.
    assert "interview_priya" in marcus_docs
    texts = {m.quote.text for m in inv1.index.mentions["Daniel Okafor"]}
    assert "Daniel" in texts and "Daniel Okafor" in texts
    # Full name wins over its parts: "Marcus Hale" is one mention, not two.
    badge = [m for m in inv1.index.mentions["Marcus Hale"] if m.quote.doc_id == "badge_log"]
    assert len(badge) == 3 and all(m.quote.text == "Marcus Hale" for m in badge)


def test_locations_are_found_with_aliases(inv1):
    lab_docs = {m.quote.doc_id for m in inv1.index.mentions["Design Lab"]}
    assert {"badge_log", "interview_daniel", "interview_lena", "chat_marcus_alex"} <= lab_docs
    garage = {m.quote.text for m in inv1.index.mentions["Parking Garage"]}
    assert "garage stairwell" in garage
