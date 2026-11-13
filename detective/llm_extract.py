"""LLM-assisted event extraction, with every LLM output checked against the evidence.

The LLM is good at reading messy prose, but it can invent things. So the LLM only *proposes*
events; this module accepts one only if:
  1. its quote appears verbatim in the document,
  2. the time it gives is actually stated in that quote,
  3. its actor is a known person who is named in the quote or is the document's speaker,
  4. its location (if any) is a known place named in the quote.
Everything else becomes a Rejection with a reason, so nothing made up reaches the timeline.

The model call is injected as `propose(doc, people, places) -> list[dict]`, so tests run
offline with a fake and the real backend lives in anthropic_backend.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from .entities import EntityMatcher
from .grounding import find_quote
from .models import Case, Document, Event, Rejection
from .segments import _CHAT_LINE
from .timeparse import find_times

Proposer = Callable[[Document, list[str], list[str]], list[dict]]


class LLMEventExtractor:
    def __init__(self, propose: Proposer):
        self.propose = propose

    def extract(self, case: Case, matcher: EntityMatcher) -> tuple[list[Event], list[Rejection]]:
        people = [p.name for p in case.people]
        places = [l.name for l in case.locations]
        events: list[Event] = []
        rejections: list[Rejection] = []
        for doc in case.documents.values():
            for n, item in enumerate(self.propose(doc, people, places), start=1):
                result = self.validate(case, doc, item, matcher, f"{doc.id}#llm{n}")
                (events if isinstance(result, Event) else rejections).append(result)
        return events, rejections

    @staticmethod
    def validate(case: Case, doc: Document, item: dict, matcher: EntityMatcher, event_id: str) -> Event | Rejection:
        def reject(reason: str) -> Rejection:
            return Rejection(doc.id, item, reason)

        quote = find_quote(case, doc.id, item.get("quote") or "")
        if quote is None:
            return reject("quote not found verbatim in source document")

        try:
            claimed = datetime.fromisoformat(item["time"])
        except (KeyError, TypeError, ValueError):
            return reject("time missing or not ISO formatted")
        stated = {t.time.replace(second=0, microsecond=0) for t in find_times(quote.text, doc.date)}
        if not stated:
            return reject("quote does not state any time")
        if claimed.replace(second=0, microsecond=0) not in stated:
            return reject("time is not the one stated in the quote")

        end_time = None
        if item.get("end_time"):
            try:
                end_time = datetime.fromisoformat(item["end_time"])
            except ValueError:
                return reject("end_time not ISO formatted")
            if end_time.replace(second=0, microsecond=0) not in stated:
                return reject("end_time is not stated in the quote")

        named = set(matcher.unique(matcher.people(quote.text)))
        actor = item.get("actor")
        if actor is not None:
            if actor not in {p.name for p in case.people}:
                return reject(f"unknown person {actor!r}")
            line_speaker = _speaker_of_line(doc, quote.start)
            if actor not in named and actor != doc.author and actor != line_speaker:
                return reject(f"actor {actor!r} is neither named in the quote nor its speaker")

        location = item.get("location")
        if location is not None:
            if location not in {l.name for l in case.locations}:
                return reject(f"unknown location {location!r}")
            if location not in matcher.unique(matcher.places(quote.text)):
                return reject(f"location {location!r} is not named in the quote")

        return Event(
            id=event_id,
            time=claimed,
            end_time=end_time,
            approximate=bool(item.get("approximate", False)),
            kind=doc.kind,
            quote=quote,
            actor=actor,
            location=location,
            people=tuple(sorted(named)),
            source="llm",
        )


def _speaker_of_line(doc: Document, offset: int) -> str | None:
    line_start = doc.body.rfind("\n", 0, offset) + 1
    line_end = doc.body.find("\n", offset)
    line = doc.body[line_start : line_end if line_end >= 0 else None]
    m = _CHAT_LINE.match(line.strip())
    return m.group("speaker").strip() if m else None
