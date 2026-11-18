import pytest

from detective.loader import load_case
from detective.pipeline import investigate
from detective.report import build_report, check_citations

from .conftest import CASE1, CASE2, CASE3


@pytest.fixture(scope="module")
def report1(inv1):
    return build_report(inv1)


def test_report_names_suspect_and_explains_confidence(report1):
    assert "**Most likely suspect: Marcus Hale**" in report1 and "**Confidence: high.**" in report1
    assert "If every assumption were wrong, the lead would be" in report1
    for section in ("## Ranking", "## Contradictions", "## Misleading evidence set aside", "## Why not the others"):
        assert section in report1


@pytest.mark.parametrize("case_dir", [CASE1, CASE2, CASE3], ids=["case1", "case2", "case3"])
def test_every_citation_in_every_report_matches_its_source(case_dir):
    inv = investigate(load_case(case_dir))
    report = build_report(inv)
    check = check_citations(inv.index.case, report)
    assert check.ok, check.problems
    assert check.quoted >= 20 and "every one matches" in report


def test_tampered_quote_is_caught(case1, report1):
    tampered = report1.replace("| Marcus Hale | Main Entrance | ENTRY”", "| Lena Torres | Main Entrance | ENTRY”", 1)
    assert tampered != report1
    problems = check_citations(case1, tampered).problems
    assert len(problems) == 1 and "does not contain" in problems[0]


def test_reference_to_a_missing_line_is_caught(case1):
    text = "Marcus was seen [badge_log:L99] and [secret_file:L1]."
    assert len(check_citations(case1, text).problems) == 2


def test_case3_report_shows_how_the_conclusion_changed(inv3, inv3_stage1):
    report = build_report(inv3, inv3_stage1)
    assert "## How the conclusion changed as evidence arrived" in report
    assert "the most likely suspect was **Iris Kemp**" in report
    assert "Now the most likely suspect is **Noah Fisk**" in report
    assert "no longer counted (+2.0): Records put Iris Kemp at Lab Wing" in report
