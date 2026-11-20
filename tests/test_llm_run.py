import json

from detective.llm_run import run_all, run_case

from .conftest import CASE1, CASES


def fake_propose(doc, people, places):
    if doc.id != "interview_marcus":
        return []
    return [{"quote": "I left the office at 6 PM and went straight home.", "time": "2026-03-12T18:00",
             "actor": "Marcus Hale", "location": None, "approximate": False},
            {"quote": "I came back for my charger at 7:40 PM.", "time": "2026-03-12T19:40",
             "actor": "Marcus Hale", "location": None, "approximate": False}]


def fake_investigator(case, assessment):
    return [{"suspect": "Marcus Hale", "label": "claim", "weight": 1, "reasoning": "Agreed a handover time.",
             "quotes": [{"doc": "chat_marcus_alex", "text": "Thursday evening works."}]},
            {"suspect": "Lena Torres", "label": "fact", "weight": 2, "reasoning": "Invented.",
             "quotes": [{"doc": "cctv_summary", "text": "Lena Torres carries the laptop out."}]}]


def fake_answerer(question, evidence, rules_answer):
    return {"answer": "Marcus.", "quotes": [{"doc": "badge_log", "text": "2026-03-12 19:44 | Marcus Hale | Design Lab | ENTRY"},
                                            {"doc": "badge_log", "text": "made up"}]}


def test_run_case_records_accepted_and_rejected():
    r = run_case(CASE1, fake_propose, fake_investigator, fake_answerer)
    assert r["events"]["proposed"] == 2 and r["events"]["rejected"] == 1
    assert r["steps"]["accepted"] == 1 and r["steps"]["rejected"] == 1
    assert r["conclusion"]["rules"] == r["conclusion"]["with_llm"] == "Marcus Hale"
    assert all(len(a["rejected_quotes"]) == 1 for a in r["answers"])


def test_run_all_writes_json_and_summary(tmp_path):
    results = run_all(CASES, tmp_path, fake_propose, fake_investigator, fake_answerer)
    assert len(results) == 3
    assert json.loads((tmp_path / "case1_missing_laptop.json").read_text())["events"]["rejected"] == 1
    assert "| The Leaked Formula |" in (tmp_path / "SUMMARY.md").read_text()
