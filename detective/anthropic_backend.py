"""Claude-backed proposers: events for LLMEventExtractor, reasoning steps for the investigator.

Requires `pip install anthropic pydantic` and credentials (ANTHROPIC_API_KEY or `ant auth login`).
Imported lazily so the rest of the system and the test suite run without network access.
"""

from __future__ import annotations

from .models import Document

MODEL = "claude-opus-5-5"

SYSTEM = """You extract timed events from one evidence document in a detective case.

Rules:
- Only extract events whose time is stated in the text. Never infer or estimate a time.
- `quote` must be copied character-for-character from the document: one contiguous span,
  normally the full sentence or log line, and it must contain the stated time.
- `time` / `end_time` are ISO 8601 (YYYY-MM-DDTHH:MM). Times with no date fall on the
  document's default date unless the text says otherwise (e.g. "the next morning").
- `actor` is who did the thing: a name from the people list, or null if the text does not
  identify them. Do not guess who an unidentified person is.
- `location` must be from the places list and named in the quote, else null.
- Skip interviewer questions; a question is not evidence.
- Set `approximate` when the text hedges ("about", "around", "a bit before")."""


def make_claude_proposer(model: str = MODEL):
    import anthropic
    from pydantic import BaseModel

    class LLMEvent(BaseModel):
        quote: str
        time: str
        end_time: str | None
        actor: str | None
        location: str | None
        approximate: bool

    class LLMEvents(BaseModel):
        events: list[LLMEvent]

    client = anthropic.Anthropic()

    def propose(doc: Document, people: list[str], places: list[str]) -> list[dict]:
        prompt = (
            f"Document id: {doc.id}\nDocument type: {doc.type}\nDefault date: {doc.date.isoformat()}\n"
            f"Speaker/author: {doc.author or 'n/a'}\n"
            f"People: {', '.join(people)}\nPlaces: {', '.join(places)}\n\n"
            f"<document>\n{doc.body}</document>"
        )
        response = client.messages.parse(
            model=model,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_format=LLMEvents,
            # Server-side fallback if a safety classifier declines the request.
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"fallbacks": "default"},
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return []
        return [e.model_dump() for e in response.parsed_output.events]

    return propose


INVESTIGATOR_SYSTEM = """You review a detective case and add reasoning steps the rules engine may have missed.

You get every evidence document and the current reasoning log. Return extra steps only where
the documents support them. Each step:
- `suspect`: one of the listed suspects.
- `label`: "fact" (only when every quote comes from a record document: badge_log, login_log,
  cctv, brief), "claim" (rests on what someone said or wrote), "assumption" (your inference),
  or "speculation" (a guess; weight must be 0).
- `weight`: -3 to 3. Positive points toward the suspect, negative away.
- `quotes`: each quote copied character-for-character from one document, with its document id.
- `reasoning`: one or two sentences.
Do not repeat steps already in the log. Never invent evidence; a step whose quote is not in the
documents is discarded."""


def make_claude_investigator(model: str = MODEL):
    import anthropic
    from pydantic import BaseModel

    class QuoteRef(BaseModel):
        doc: str
        text: str

    class LLMStep(BaseModel):
        suspect: str
        label: str
        weight: float
        quotes: list[QuoteRef]
        reasoning: str

    class LLMSteps(BaseModel):
        steps: list[LLMStep]

    client = anthropic.Anthropic()

    def propose(case, assessment) -> list[dict]:
        docs = "\n\n".join(
            f"<document id=\"{d.id}\" type=\"{d.type}\" date=\"{d.date}\">\n{d.body}</document>"
            for d in case.documents.values()
        )
        log = "\n".join(
            f"- {s.suspect} | {s.label.value} | {s.weight:+.1f} | {s.text}"
            for l in assessment.logs.values() for s in l.steps
        )
        prompt = (
            f"Case: {case.title}\nSuspects: {', '.join(p.name for p in case.suspects)}\n\n{docs}\n\n"
            f"<current_log>\n{log}\n</current_log>"
        )
        response = client.messages.parse(
            model=model,
            max_tokens=16000,
            system=INVESTIGATOR_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_format=LLMSteps,
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"fallbacks": "default"},
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return []
        return [s.model_dump() for s in response.parsed_output.steps]

    return propose


ANSWER_SYSTEM = """You answer an investigator's follow-up question about a detective case.

Use only the evidence passages provided (each is prefixed with its document id) and the rules
engine's answer. Be brief and plain. Say what the records show separately from what people
claim, and say when something is an assumption or cannot be known from the evidence.
List every passage you rely on in `quotes`, copied character-for-character with its document id.
Any quote that is not in the documents is discarded."""


def make_claude_answerer(model: str = MODEL):
    import anthropic
    from pydantic import BaseModel

    class QuoteRef(BaseModel):
        doc: str
        text: str

    class LLMAnswer(BaseModel):
        answer: str
        quotes: list[QuoteRef]

    client = anthropic.Anthropic()

    def answer(question: str, evidence: str, rules_answer: str) -> dict:
        prompt = (f"<evidence>\n{evidence}\n</evidence>\n\n<rules_answer>\n{rules_answer}\n</rules_answer>\n\n"
                  f"Question: {question}")
        response = client.messages.parse(
            model=model,
            max_tokens=4000,
            system=ANSWER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_format=LLMAnswer,
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"fallbacks": "default"},
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return {"answer": "", "quotes": []}
        return response.parsed_output.model_dump()

    return answer
