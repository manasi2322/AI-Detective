"""Presence: who was on the premises when, built only from movement records (badge log, CCTV).

Witness claims never feed into this model, so it is the reference that claims are checked against.
Unidentified people on CCTV ("a man in a grey hoodie") are not assigned to anyone.

Assumptions (reported alongside any conclusion that depends on them):
- people enter through a recorded entrance; exits may go unrecorded (an open stay has no end);
- before someone's first recorded entry they were not on the premises.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import MOVEMENT_TYPES, Case, Event, Quote

DUPLICATE_GAP = timedelta(minutes=10)  # badge + CCTV of the same exit, a minute apart

_IN_FIELD = {"ENTRY", "ENTER", "IN"}
_OUT_FIELD = {"EXIT", "OUT"}
_IN_WORDS = re.compile(r"\b(enters|entered|arrives|arrived|comes in|came in|badges in)\b", re.IGNORECASE)
_OUT_WORDS = re.compile(r"\b(leaves|left|exits|exited|departs|departed|badges out)\b", re.IGNORECASE)

ASSUME_COMPLETE = "Assumes every entry to the premises is recorded; a missing record is not proof of absence."


@dataclass(frozen=True)
class Movement:
    person: str
    time: datetime
    location: str | None
    direction: str | None  # "in" | "out" | None (seen there)
    quote: Quote


@dataclass(frozen=True)
class Stay:
    """A stretch of time on the premises. None means the record does not say (no entry / no exit seen)."""

    person: str
    start: datetime | None
    end: datetime | None
    start_quote: Quote | None
    end_quote: Quote | None

    def covers(self, t: datetime) -> bool:
        return (self.start is None or self.start <= t) and (self.end is None or t <= self.end)

    def overlaps(self, a: datetime, b: datetime) -> bool:
        return (self.start is None or self.start <= b) and (self.end is None or a <= self.end)

    def quotes(self) -> list[Quote]:
        return [q for q in (self.start_quote, self.end_quote) if q]

    def describe(self) -> str:
        a = self.start.strftime("%m-%d %H:%M") if self.start else "?"
        b = self.end.strftime("%m-%d %H:%M") if self.end else "? (no exit recorded)"
        return f"{a} -> {b}"


def _direction(e: Event) -> str | None:
    fields = [f.strip().upper() for f in e.quote.text.split("|")]
    if len(fields) > 1 and fields[-1] in _IN_FIELD:
        return "in"
    if len(fields) > 1 and fields[-1] in _OUT_FIELD:
        return "out"
    if _IN_WORDS.search(e.quote.text):
        return "in"
    if _OUT_WORDS.search(e.quote.text):
        return "out"
    return None


class Presence:
    def __init__(self, case: Case, events: list[Event]):
        self.case = case
        self._moves: dict[str, list[Movement]] = {p.name: [] for p in case.people}
        for e in events:
            if case.documents[e.doc_id].type not in MOVEMENT_TYPES:
                continue
            for person in e.people or ((e.actor,) if e.actor else ()):
                self._moves[person].append(Movement(person, e.time, e.location, _direction(e), e.quote))
        for moves in self._moves.values():
            moves.sort(key=lambda m: (m.time, m.quote.doc_id))
        self._stays = {p: self._build_stays(p, m) for p, m in self._moves.items()}

    def _is_entrance(self, location: str | None) -> bool:
        loc = self.case.location(location)
        return bool(loc and loc.entrance)

    def _build_stays(self, person: str, moves: list[Movement]) -> list[Stay]:
        stays: list[Stay] = []
        open_: Movement | None = None
        for m in moves:
            if not self._is_entrance(m.location) or m.direction is None:
                continue
            if m.direction == "in":
                if open_ is None:
                    open_ = m  # a second "in" while inside is the CCTV view of the same entry
            elif open_ is not None:
                stays.append(Stay(person, open_.time, m.time, open_.quote, m.quote))
                open_ = None
            elif not (stays and stays[-1].end and m.time - stays[-1].end <= DUPLICATE_GAP):
                stays.append(Stay(person, None, m.time, None, m.quote))
        if open_ is not None:
            stays.append(Stay(person, open_.time, None, open_.quote, None))
        # Seen inside (e.g. the Design Lab reader) outside any known stay: on site at that moment.
        for m in moves:
            if not self._is_entrance(m.location) and not any(s.covers(m.time) for s in stays):
                stays.append(Stay(person, m.time, m.time, m.quote, m.quote))
        return sorted(stays, key=lambda s: s.start or s.end)

    def movements(self, person: str) -> list[Movement]:
        return list(self._moves.get(person, []))

    def stays(self, person: str) -> list[Stay]:
        return list(self._stays.get(person, []))

    def between(self, person: str, a: datetime, b: datetime, location: str | None = None) -> list[Movement]:
        return [m for m in self._moves.get(person, []) if a <= m.time <= b and (location is None or m.location == location)]

    def state_at(self, person: str, t: datetime) -> tuple[str, list[Quote]]:
        """'on site' | 'off site' | 'unknown', with the records that show it."""
        stays = self._stays.get(person, [])
        for s in stays:
            if s.covers(t):
                return "on site", s.quotes()
        before = [s for s in stays if s.end is not None and s.end < t]
        after = [s for s in stays if s.start is not None and s.start > t]
        if before:
            return "off site", [q for q in (before[-1].end_quote, after[0].start_quote if after else None) if q]
        if after:
            return "off site", [after[0].start_quote]
        return "unknown", []
