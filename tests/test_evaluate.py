import json
import shutil

from detective.cli import main
from detective.evaluate import evaluate_all, evaluate_case

from .conftest import CASE1, CASES


def test_all_cases_solved_and_every_check_passes():
    results = evaluate_all(CASES)
    assert [r.case_id for r in results] == ["case1_missing_laptop", "case2_gallery_switch", "case3_leaked_formula"]
    for r in results:
        assert r.solved and r.score == 1.0, [c for c in r.checks if not c.passed]
        assert len(r.checks) >= 15


def test_evaluation_catches_a_wrong_answer(tmp_path):
    copy = tmp_path / "case1"
    shutil.copytree(CASE1, copy)
    sol = json.loads((copy / "solution.json").read_text())
    sol["culprit"] = "Lena Torres"
    (copy / "solution.json").write_text(json.dumps(sol))
    r = evaluate_case(copy)
    assert not r.solved and r.score < 1.0
    assert not next(c for c in r.checks if c.name == "names the culprit").passed


def test_evaluate_command(capsys):
    assert main(["evaluate", str(CASES)]) == 0
    out = capsys.readouterr().out
    assert "Culprit named correctly in 3/3 cases" in out and "100%" in out


def test_report_command_writes_a_checked_report(tmp_path, capsys):
    out = tmp_path / "report.md"
    assert main(["report", str(CASES / "case3_leaked_formula"), "--out", str(out)]) == 0
    text = out.read_text()
    assert "## How the conclusion changed" in text and "## Citation check" in text
