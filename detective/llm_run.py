"""Live LLM run: let Claude extract events, add reasoning steps and answer questions on every case,
then record exactly what was accepted and what was rejected (and why).

    export ANTHROPIC_API_KEY=...      # or: ant auth login
    python -m detective llm-run       # writes samples/llm_runs/<case>.json and samples/llm_runs/SUMMARY.md

The rules engine runs alongside, so the record shows whether Claude's extra steps changed the
conclusion. Nothing Claude proposes reaches the results without passing the grounding checks.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .loader import load_case
from .pipeline import investigate
from .qa import answer_with_llm

QUESTIONS = ["Who did it, and why?", "Which statements are lies?", "What evidence is misleading?"]


def run_case(case_dir: str | Path, propose: Callable, investigator: Callable, answerer: Callable) -> dict:
    case = load_case(case_dir)
    proposed = {"events": 0}

    def counting_propose(doc, people, places):
        items = propose(doc, people, places)
        proposed["events"] += len(items)
        return items

    rules = investigate(case)
    llm = investigate(case, propose=counting_propose, investigator=investigator)
    llm_events = [e for e in llm.index.events if e.source == "llm"]
    llm_steps = [s for log in llm.assessment.logs.values() for s in log.steps if s.source == "llm"]
    answers = []
    for q in QUESTIONS:
        a = answer_with_llm(llm, q, answerer)
        answers.append({"question": q, "source": a.source, "answer": a.text,
                        "quotes": [q_.cite() for _, q_ in a.citations], "rejected_quotes": a.rejected})
    return {
        "case": case.id, "title": case.title,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "events": {"proposed": proposed["events"], "added": len(llm_events),
                   "rejected": len(llm.index.rejections),
                   "rejections": [{"doc": r.doc_id, "reason": r.reason, "quote": r.item.get("quote")}
                                  for r in llm.index.rejections]},
        "steps": {"accepted": len(llm_steps), "rejected": len(llm.assessment.rejections),
                  "accepted_steps": [{"suspect": s.suspect, "label": s.label.value, "weight": s.weight,
                                      "text": s.text, "quotes": [q.cite() for q in s.evidence]} for s in llm_steps],
                  "rejections": [{"reason": r.reason, "item": r.item} for r in llm.assessment.rejections]},
        "conclusion": {"rules": rules.assessment.most_likely, "with_llm": llm.assessment.most_likely,
                       "rules_confidence": rules.assessment.confidence()[0],
                       "with_llm_confidence": llm.assessment.confidence()[0],
                       "scores_with_llm": {l.suspect: l.score for l in llm.assessment.ranking()}},
        "answers": answers,
    }


def summarise(results: list[dict]) -> str:
    out = ["# Live LLM run", "",
           "| Case | Events proposed | Events rejected | Steps accepted | Steps rejected | Answer quotes dropped "
           "| Rules verdict | Verdict with LLM |",
           "|---|---|---|---|---|---|---|---|"]
    for r in results:
        dropped = sum(len(a["rejected_quotes"]) for a in r["answers"])
        out.append(f"| {r['title']} | {r['events']['proposed']} | {r['events']['rejected']} | "
                   f"{r['steps']['accepted']} | {r['steps']['rejected']} | {dropped} | "
                   f"{r['conclusion']['rules']} | {r['conclusion']['with_llm']} |")
    out += ["", "Every rejection is listed with its reason in the per-case JSON files."]
    return "\n".join(out) + "\n"


def run_all(cases_dir: str | Path = "cases", out_dir: str | Path = "samples/llm_runs",
            propose=None, investigator=None, answerer=None) -> list[dict]:
    if propose is None:
        from .anthropic_backend import make_claude_answerer, make_claude_investigator, make_claude_proposer

        propose, investigator, answerer = make_claude_proposer(), make_claude_investigator(), make_claude_answerer()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for d in sorted(p for p in Path(cases_dir).iterdir() if (p / "case.json").exists()):
        r = run_case(d, propose, investigator, answerer)
        (out / f"{r['case']}.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
        results.append(r)
    (out / "SUMMARY.md").write_text(summarise(results), encoding="utf-8")
    return results


def check_credentials() -> str | None:
    """None if the Anthropic SDK can authenticate, else a message saying what to do."""
    try:
        import anthropic
    except ImportError:
        return "The anthropic package is not installed: pip install anthropic pydantic"
    try:
        anthropic.Anthropic().models.list(limit=1)
    except anthropic.AuthenticationError:
        return "The API key was rejected. Check ANTHROPIC_API_KEY."
    except anthropic.APIConnectionError:
        return "Could not reach the Anthropic API (network)."
    except Exception as e:  # missing credentials raise before any request is sent
        return f"No Claude credentials found ({type(e).__name__}). Set ANTHROPIC_API_KEY or run `ant auth login`."
    return None
