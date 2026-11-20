import json
import threading
import urllib.error
import urllib.request

import pytest

from detective.web import ApiError, DetectiveApp, serve

from .conftest import CASES

SAMPLE = (CASES.parent / "samples" / "new_evidence" / "case1_sam_returns.txt").read_text()


@pytest.fixture(scope="module")
def app():
    return DetectiveApp(CASES)


def test_case_overview(app):
    d = app.case({"case": "case2_gallery_switch"})
    assert d["conclusion"]["suspect"] == "Victor Lane" and d["conclusion"]["confidence"] == "high"
    assert [s["name"] for s in d["suspects"]][0] == "Victor Lane"
    assert any(e["disputed"] for e in d["timeline"])  # the guard's badge swipe
    assert d["contradictions"] and d["speculation"]


def test_ask_and_reassess(app):
    a = app.ask({"case": "case1_missing_laptop", "question": "Did Marcus lie?"})
    assert a["text"].startswith("Yes.") and {"statement", "record"} <= {c["kind"] for c in a["citations"]}
    r = app.reassess({"case": "case3_leaked_formula", "stage": 1, "new_stage": 2})
    assert r["leader_changed"] and (r["leader_before"], r["leader_after"]) == ("Iris Kemp", "Noah Fisk")
    r = app.reassess({"case": "case1_missing_laptop", "new_evidence": SAMPLE})
    assert not r["leader_changed"] and r["overview"]["suspects"][1]["name"] == "Sam Whitfield"


def test_unknown_case_and_bad_evidence_are_refused(app):
    with pytest.raises(ApiError) as e:
        app.case({"case": "../../etc"})
    assert e.value.status == 404
    with pytest.raises(ApiError) as e:
        app.case({"case": "case1_missing_laptop", "added": [SAMPLE, SAMPLE]})
    assert e.value.status == 400


def test_report_and_document(app):
    md = app.report({"case": "case3_leaked_formula"})["markdown"]
    assert "## How the conclusion changed" in md and "every one matches" in md
    doc = app.document({"case": "case1_missing_laptop", "doc": "badge_log"})
    assert doc["lines"][5] == "2026-03-12 19:41 | Marcus Hale | Main Entrance | ENTRY"


def test_http_server_end_to_end():
    server = serve(CASES, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        page = urllib.request.urlopen(base + "/?case=case2_gallery_switch").read().decode()
        assert "<title>AI Detective</title>" in page
        cases = json.load(urllib.request.urlopen(base + "/api/cases"))
        assert [c["stages"] for c in cases] == [[1], [1], [1, 2]]
        req = urllib.request.Request(base + "/api/ask", data=json.dumps(
            {"case": "case2_gallery_switch", "question": "Did Celia lie?"}).encode(), method="POST")
        assert json.load(urllib.request.urlopen(req))["text"].startswith("Yes.")
        bad = urllib.request.Request(base + "/api/ask", data=b"not json", method="POST")
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(bad)
        assert e.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
