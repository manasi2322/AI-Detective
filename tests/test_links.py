def test_unnamed_cctv_figure_matched_as_assumption(inv1, inv_holdout, solution1, holdout_solution):
    for inv, sol in ((inv1, solution1), (inv_holdout, holdout_solution)):
        found = {(m.cctv.cite(), m.person) for m in inv.cctv_matches}
        assert found == {(x["cctv"], x["person"]) for x in sol["cctv_matches"]}
        assert all(m.label == "assumption" for m in inv.cctv_matches)


def test_cctv_match_cites_the_records_it_relies_on(inv1):
    first = next(m for m in inv1.cctv_matches if m.refers_to is None)
    assert [q.cite() for q in first.records] == ["badge_log:L6", "badge_log:L7"]
    second = next(m for m in inv1.cctv_matches if m.refers_to is not None)
    assert second.refers_to == first.cctv and "same" in second.cctv.text


def test_hidden_connection_and_denial(inv1, inv_holdout, solution1, holdout_solution):
    for inv, sol in ((inv1, solution1), (inv_holdout, holdout_solution)):
        found = {(c.suspect, c.party, c.denial is not None) for c in inv.connections}
        assert found == {(x["suspect"], x["party"], x["denied"]) for x in sol["connections"]}
    [c] = inv1.connections
    assert c.denial.text == "I've never talked to anyone there."
