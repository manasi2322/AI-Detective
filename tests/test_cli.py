from detective.cli import main

from .conftest import CASE1


def test_analyze_command_reports_the_contradiction(capsys):
    assert main(["analyze", str(CASE1)]) == 0
    out = capsys.readouterr().out
    assert "Marcus Hale (suspect): alibi BROKEN" in out
    assert "CONTRADICTED" in out and "[badge_log:L6]" in out
    assert "SPECULATION" in out and "OPPORTUNITY" in out


def test_investigate_motives_and_links_commands(capsys):
    assert main(["investigate", str(CASE1)]) == 0
    out = capsys.readouterr().out
    assert "most likely: Marcus Hale" in out and "confidence: high" in out
    assert main(["motives", str(CASE1)]) == 0 and "gain (reported by Alex Brandt)" in capsys.readouterr().out
    assert main(["links", str(CASE1)]) == 0
    out = capsys.readouterr().out
    assert "-> Marcus Hale  (ASSUMPTION)" in out and "denial:" in out
