"""Opportunity: could each suspect have been at the scene while the crime could have happened?

The window's two ends come from case.json, but each one is a quote that must exist word for word
in the evidence, and its time is read from that quote. Who was where comes only from movement
records, never from what witnesses say about themselves or others.

Levels: AT_SCENE (a record puts them at the scene inside the window)
        ON_SITE  (on the premises during the window, no record at the scene)
        NONE     (no record puts them on the premises during the window)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .grounding import find_quote
from .models import Case, Quote
from .presence import ASSUME_COMPLETE, Presence
from .timeparse import time_span


class Access(str, Enum):
    AT_SCENE = "at scene"
    ON_SITE = "on site"
    NONE = "no recorded presence"


@dataclass(frozen=True)
class Window:
    scene: str
    start: datetime
    end: datetime
    start_quote: Quote
    end_quote: Quote

    def describe(self) -> str:
        return f"{self.start:%m-%d %H:%M} -> {self.end:%m-%d %H:%M} at {self.scene}"


@dataclass
class Opportunity:
    person: str
    access: Access
    evidence: list[Quote]
    explanation: str
    assumptions: list[str] = field(default_factory=list)


class UngroundedWindow(ValueError):
    pass


def resolve_window(case: Case) -> Window | None:
    if not case.scene or not case.window:
        return None
    bounds = {}
    for side in ("start", "end"):
        spec = case.window[side]
        quote = find_quote(case, spec["doc"], spec["quote"])
        if quote is None:
            raise UngroundedWindow(f"window {side} quote is not in {spec['doc']!r}: {spec['quote']!r}")
        span = time_span(quote.text, case.documents[quote.doc_id].date)
        if span is None:
            raise UngroundedWindow(f"window {side} quote states no time: {quote.text!r}")
        bounds[side] = (span.start, quote)
    (start, sq), (end, eq) = bounds["start"], bounds["end"]
    if end <= start:
        raise UngroundedWindow("window ends before it starts")
    return Window(case.scene, start, end, sq, eq)


def assess_opportunity(case: Case, presence: Presence, window: Window) -> dict[str, Opportunity]:
    out: dict[str, Opportunity] = {}
    for person in (p.name for p in case.suspects):
        at_scene = presence.between(person, window.start, window.end, location=window.scene)
        if at_scene:
            times = ", ".join(f"{m.time:%H:%M} [{m.quote.cite()}]" for m in at_scene)
            out[person] = Opportunity(person, Access.AT_SCENE, [m.quote for m in at_scene],
                                      f"Records put {person} at {window.scene} at {times}, inside the window.")
            continue
        stays = [s for s in presence.stays(person) if s.overlaps(window.start, window.end)]
        if stays:
            spans = "; ".join(s.describe() for s in stays)
            out[person] = Opportunity(person, Access.ON_SITE, [q for s in stays for q in s.quotes()],
                                      f"On the premises during the window ({spans}), but no record puts "
                                      f"{person} at {window.scene}.", [ASSUME_COMPLETE])
            continue
        _, why = presence.state_at(person, window.start)
        detail = f" (last record: {', '.join(q.cite() for q in why)})" if why else ""
        out[person] = Opportunity(person, Access.NONE, why,
                                  f"No record puts {person} on the premises during the window{detail}.",
                                  [ASSUME_COMPLETE])
    return out
