"""Rule-based event extraction: every sentence or log line that states a time becomes an Event.

The rules are deliberately conservative:
- interviewer questions never become events (a question is not evidence);
- the actor is the speaker when the format tells us, otherwise a person named in the line,
  otherwise None. An unidentified figure on CCTV stays unidentified.
"""

from __future__ import annotations

from .entities import EntityMatcher
from .models import Case, Event
from .segments import Segment
from .timeparse import time_span


def extract_events(case: Case, segments: list[Segment], matcher: EntityMatcher) -> list[Event]:
    events: list[Event] = []
    counters: dict[str, int] = {}
    for seg in segments:
        if seg.role == "question":
            continue
        doc = case.documents[seg.quote.doc_id]
        span = time_span(seg.text, doc.date)
        if span is None:
            continue
        people = tuple(matcher.unique(matcher.people(seg.text)))
        places = matcher.unique(matcher.places(seg.text))
        actor = seg.speaker or (people[0] if people else None)
        counters[doc.id] = counters.get(doc.id, 0) + 1
        events.append(
            Event(
                id=f"{doc.id}#{counters[doc.id]}",
                time=span.start,
                end_time=span.end,
                approximate=span.approximate,
                kind=doc.kind,
                quote=seg.quote,
                actor=actor,
                location=places[0] if places else None,
                people=people,
                source="rules",
            )
        )
    return events
