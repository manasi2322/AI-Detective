from detective.cli import main

from .conftest import CASE1


def test_analyze_command_reports_the_contradiction(capsys):
    assert main(["analyze", str(CASE1)]) == 0
    out = capsys.readouterr().out
    assert "Marcus Hale (suspect): alibi BROKEN" in out
    assert "CONTRADICTED" in out and "[badge_log:L6]" in out
    assert "SPECULATION" in out and "OPPORTUNITY" in out
