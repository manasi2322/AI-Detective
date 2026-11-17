from detective.investigator import WEIGHTS
from detective.motive import MotiveType


def _types(inv, person):
    return sorted({m.type.value for m in inv.motives if m.person == person})


def test_motives_match_the_answer_key(inv1, inv_holdout, solution1, holdout_solution):
    for inv, sol in ((inv1, solution1), (inv_holdout, holdout_solution)):
        for person, expected in sol["motives"].items():
            assert _types(inv, person) == sorted(expected), person


def test_culprit_motive_is_reported_by_someone_else_and_cited(inv1):
    [m] = [m for m in inv1.motives if m.person == "Marcus Hale"]
    assert m.type is MotiveType.GAIN and not m.self_reported and m.reported_by == "Alex Brandt"
    assert m.quote.cite() == "chat_marcus_alex:L1"


def test_guesses_are_never_motives(inv1):
    # "Marcus has seemed stressed about money lately." is speculation, not a money motive.
    assert not any("seemed" in m.quote.text for m in inv1.motives)
    assert not {s.quote for s in inv1.speculation} & {m.quote for m in inv1.motives}


def test_culprit_has_the_strongest_motive(inv1, inv_holdout, solution1, holdout_solution):
    for inv, sol in ((inv1, solution1), (inv_holdout, holdout_solution)):
        strongest = {}
        for m in inv.motives:
            strongest[m.person] = max(strongest.get(m.person, 0), WEIGHTS[m.type])
        assert max(strongest, key=strongest.get) == sol["culprit"]
