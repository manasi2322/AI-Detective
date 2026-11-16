def test_priyas_guess_about_lena_is_flagged(inv1):
    [s] = [s for s in inv1.speculation if "Lena Torres" in s.about]
    assert s.speaker == "Priya Nair" and s.marker == "probably" and s.category == "guess"
    assert s.quote.text == "Honestly, it was probably Lena."


def test_impressions_are_flagged_too(inv1):
    [s] = [s for s in inv1.speculation if "Marcus Hale" in s.about]
    assert s.category == "impression" and s.marker == "seemed"


def test_exactly_the_known_speculation_is_flagged(inv1, solution1):
    flagged = {(s.speaker, a) for s in inv1.speculation for a in s.about}
    assert flagged == {(x["speaker"], x["about"]) for x in solution1["speculation"]}
    assert all(inv1.index.case.documents[s.quote.doc_id].kind.value == "claim" for s in inv1.speculation)


def test_speculation_never_becomes_evidence(inv1):
    spec = {s.quote for s in inv1.speculation}
    assert not spec & {c.quote for c in inv1.claims}
    assert not spec & {q for a in inv1.alibis.values() for c in a.checks for q in c.evidence}
    assert not spec & {q for o in inv1.opportunity.values() for q in o.evidence}
