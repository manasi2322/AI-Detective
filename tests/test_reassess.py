from pathlib import Path

import pytest

from detective.chat import Session, run_chat
from detective.loader import add_evidence, document_from_text, load_case
from detective.pipeline import investigate
from detective.reassess import compare

from .conftest import CASE1, CASE3

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "new_evidence" / "case1_sam_returns.txt"


def test_uncovering_case3_evidence_changes_the_conclusion(inv3_stage1, inv3):
    c = compare(inv3_stage1, inv3)
    assert c.leader_changed and (c.leader_before, c.leader_after) == ("Iris Kemp", "Noah Fisk")
    assert {d.id for d in c.added} == {"cctv", "chat_noah_rhea"}
    assert [d.record.cite() for d in c.new_disputes] == ["login_log:L1"]
    iris = next(x for x in c.changes if x.suspect == "Iris Kemp")
    assert iris.delta == -2.0 and any("Lab Wing at 22:15" in s.text for s in iris.gone)


def test_added_evidence_is_reassessed_from_scratch(case1, inv1):
    doc = document_from_text(SAMPLE.read_text(), SAMPLE)
    after = investigate(add_evidence(case1, [doc]))
    c = compare(inv1, after)
    sam = next(x for x in c.changes if x.suspect == "Sam Whitfield")
    assert sam.before < 0 < sam.after and not c.leader_changed
    assert after.alibis["Sam Whitfield"].status == "broken"
    assert "badge_log_annex" not in case1.documents  # the original case is untouched


def test_adding_a_document_twice_is_refused(case1):
    doc = document_from_text(SAMPLE.read_text(), SAMPLE)
    with pytest.raises(ValueError, match="already in the case"):
        add_evidence(add_evidence(case1, [doc]), [doc])


def test_session_uncovers_stages_in_order():
    s = Session(CASE3, stage=1)
    assert s.inv.assessment.most_likely == "Iris Kemp"
    assert "CHANGED: Iris Kemp" in s.uncover()
    assert s.inv.assessment.most_likely == "Noah Fisk"
    assert s.uncover() == "There is no more evidence to uncover in this case."


def test_chat_runs_questions_and_commands(tmp_path):
    out = []
    report = tmp_path / "r.md"
    run_chat(CASE1, ["Did Marcus lie?", f":add {SAMPLE}", ":who", f":report {report}", ":bogus", ":quit",
                     "never reached"], out.append)
    text = "\n".join(out)
    assert "Yes. 2 statements by Marcus Hale" in text
    assert "Sam Whitfield          -0.5    +6.0" in text
    assert "Unknown command :bogus" in text and "never reached" not in text
    assert "## How the conclusion changed" in report.read_text()


def test_stage_one_of_case3_hides_later_evidence():
    assert "cctv" not in load_case(CASE3, stage=1).documents
