"""Local web UI: python -m detective web [--port 8000], then open http://127.0.0.1:8000

Standard library only. The server keeps no state: every request names the case, the evidence
stage and any evidence the investigator has added, and the investigation runs again from
scratch. The browser keeps the session (stage, added documents, question history).

JSON API (used by the page, also handy for scripting):
  GET  /api/cases                                -> list of cases
  POST /api/case     {case, stage?, added?}      -> ranking, reasoning, timeline, contradictions, documents
  POST /api/ask      {case, question, stage?, added?}
  POST /api/reassess {case, stage?, added?, new_stage?, new_evidence?} -> before/after comparison
  POST /api/report   {case, stage?, added?}      -> Markdown report (citations checked)
  POST /api/document {case, doc, stage?, added?} -> the document text
"""

from __future__ import annotations

import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .loader import add_evidence, case_stages, document_from_text, load_case
from .models import EvidenceKind, Quote
from .pipeline import investigate
from .qa import ask
from .reassess import compare
from .report import build_report

MAX_BODY = 200_000  # bytes; evidence documents are small text files
STATIC = Path(__file__).resolve().parent / "web_static" / "index.html"


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _q(q: Quote) -> dict:
    return {"doc": q.doc_id, "line": q.line, "text": q.text, "cite": q.cite()}


class DetectiveApp:
    def __init__(self, cases_root: str | Path = "cases"):
        self.root = Path(cases_root)

    # -- helpers ---------------------------------------------------------------------------
    def _case_dirs(self) -> dict[str, Path]:
        return {p.name: p for p in sorted(self.root.iterdir()) if (p / "case.json").exists()}

    def _dir(self, case_id: str) -> Path:
        dirs = self._case_dirs()
        if case_id not in dirs:  # only known case folders: no paths from the client
            raise ApiError(HTTPStatus.NOT_FOUND, f"unknown case {case_id!r}")
        return dirs[case_id]

    def _investigate(self, body: dict):
        case_dir = self._dir(str(body.get("case", "")))
        stages = case_stages(case_dir)
        stage = body.get("stage") or stages[-1]
        case = load_case(case_dir, stage=int(stage))
        added = body.get("added") or []
        if added:
            try:
                case = add_evidence(case, [document_from_text(t, f"added_{i}") for i, t in enumerate(added)])
            except ValueError as e:
                raise ApiError(HTTPStatus.BAD_REQUEST, str(e)) from e
        return investigate(case), stages, int(stage)

    # -- endpoints --------------------------------------------------------------------------
    def cases(self) -> list[dict]:
        out = []
        for cid, d in self._case_dirs().items():
            spec = json.loads((d / "case.json").read_text(encoding="utf-8"))
            out.append({"id": cid, "title": spec["title"], "difficulty": spec.get("difficulty", ""),
                        "summary": spec.get("summary", ""), "stages": case_stages(d)})
        return out

    def case(self, body: dict) -> dict:
        inv, stages, stage = self._investigate(body)
        return self._overview(inv, stages, stage)

    def _overview(self, inv, stages, stage) -> dict:
        case = inv.index.case
        a = inv.assessment
        level, reasons = a.confidence_reasons()
        suspects = []
        for log in a.ranking():
            suspects.append({
                "name": log.suspect, "score": log.score,
                "role": next(p.role for p in case.people if p.name == log.suspect),
                "alibi": inv.alibis[log.suspect].status,
                "opportunity": inv.opportunity[log.suspect].access.value if log.suspect in inv.opportunity else None,
                "steps": [{"label": s.label.value, "weight": s.weight, "kind": s.kind, "text": s.text,
                           "source": s.source, "tested": _q(s.tested) if s.tested else None,
                           "evidence": [_q(q) for q in s.evidence if q != s.tested]} for s in log.steps],
            })
        disputed = {d.record for d in inv.disputes}
        timeline = [{"time": e.time.strftime("%m-%d %H:%M"), "kind": e.kind.value, "actor": e.actor,
                     "location": e.location, "disputed": e.quote in disputed, "quote": _q(e.quote)}
                    for e in inv.timeline.events]
        contradictions = []
        for al in inv.alibis.values():
            for c in al.checks + al.sightings:
                if c.verdict.value == "contradicted":
                    contradictions.append({"text": c.explanation, "claim": _q(c.claim.quote),
                                           "evidence": [_q(q) for q in c.evidence]})
        contradictions += [{"text": c.explanation(), "claim": _q(c.a.claim.quote), "evidence": [_q(c.b.claim.quote)]}
                           for c in inv.conflicts]
        contradictions += [{"text": f"{c.suspect} denied contact with {c.party}, but messages show it.",
                            "claim": _q(c.denial), "evidence": [_q(q) for q in c.messages]}
                           for c in inv.connections if c.denial]
        return {
            "case": {"id": case.id, "title": case.title, "difficulty": case.difficulty, "summary": case.summary,
                     "date": case.incident_date.isoformat(), "stage": stage, "stages": stages},
            "conclusion": {"suspect": a.most_likely, "confidence": level, "reasons": reasons},
            "suspects": suspects,
            "timeline": timeline,
            "contradictions": contradictions,
            "disputes": [{"text": d.explanation, "record": _q(d.record), "cctv": _q(d.cctv)} for d in inv.disputes],
            "speculation": [{"speaker": s.speaker, "about": list(s.about), "quote": _q(s.quote)} for s in inv.speculation],
            "documents": [{"id": d.id, "title": d.title, "type": d.type, "stage": d.stage,
                           "kind": "record" if d.kind is EvidenceKind.RECORD else "statement"}
                          for d in case.documents.values()],
        }

    def ask(self, body: dict) -> dict:
        question = str(body.get("question", "")).strip()
        if not question:
            raise ApiError(HTTPStatus.BAD_REQUEST, "question is empty")
        inv, _, _ = self._investigate(body)
        a = ask(inv, question)
        return {"question": question, "intent": a.intent, "text": a.text,
                "citations": [{"kind": k, **_q(q)} for k, q in a.citations]}

    def reassess(self, body: dict) -> dict:
        before, stages, stage = self._investigate(body)
        after_body = dict(body)
        if body.get("new_stage"):
            after_body["stage"] = int(body["new_stage"])
        if body.get("new_evidence"):
            after_body["added"] = list(body.get("added") or []) + [str(body["new_evidence"])]
        after, _, after_stage = self._investigate(after_body)
        c = compare(before, after)
        return {
            "text": c.render(), "leader_changed": c.leader_changed,
            "leader_before": c.leader_before, "leader_after": c.leader_after,
            "changes": [{"suspect": x.suspect, "before": x.before, "after": x.after, "delta": x.delta,
                         "gone": [s.text for s in x.gone], "new": [s.text for s in x.new]} for x in c.changes],
            "added": [asdict(d) | {"date": d.date.isoformat()} for d in c.added],
            "overview": self._overview(after, stages, after_stage),
        }

    def report(self, body: dict) -> dict:
        inv, stages, stage = self._investigate(body)
        earlier = None
        if stage > stages[0] and not body.get("added"):
            earlier = investigate(load_case(self._dir(body["case"]), stage=stages[0]))
        return {"markdown": build_report(inv, earlier)}

    def document(self, body: dict) -> dict:
        inv, _, _ = self._investigate(body)
        doc = inv.index.case.documents.get(str(body.get("doc", "")))
        if doc is None:
            raise ApiError(HTTPStatus.NOT_FOUND, "unknown document")
        return {"id": doc.id, "title": doc.title, "type": doc.type, "date": doc.date.isoformat(),
                "author": doc.author, "lines": doc.body.splitlines(),
                "kind": "record" if doc.kind is EvidenceKind.RECORD else "statement"}


def make_handler(app: DetectiveApp):
    routes = {"/api/case": app.case, "/api/ask": app.ask, "/api/reassess": app.reassess,
              "/api/report": app.report, "/api/document": app.document}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the terminal quiet
            pass

        def _send(self, status: int, payload, content_type="application/json; charset=utf-8"):
            data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlsplit(self.path).path  # ignore ?case=... (read by the page itself)
            if path in ("/", "/index.html"):
                self._send(200, STATIC.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/cases":
                self._send(200, app.cases())
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            handler = routes.get(urlsplit(self.path).path)
            if handler is None:
                return self._send(404, {"error": "not found"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._send(413, {"error": "request too large"})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ApiError(400, "body must be a JSON object")
                self._send(200, handler(body))
            except ApiError as e:
                self._send(e.status, {"error": str(e)})
            except (json.JSONDecodeError, ValueError) as e:
                self._send(400, {"error": str(e)})

    return Handler


def serve(cases_root: str | Path = "cases", port: int = 8000, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(DetectiveApp(cases_root)))
