"""Claude-backed proposer for LLMEventExtractor.

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
