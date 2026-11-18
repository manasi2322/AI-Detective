"""Find clock times in free text and resolve them to datetimes.

Handles "2026-03-12 19:44", "6:15 PM", "6 PM", "19:44", "8:45 the next morning",
hedges such as "about"/"around" (marked approximate) and ranges ("from 7 PM to 8 PM").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

_FULL = re.compile(r"\b(\d{4}-\d{2}-\d{2})[ T](\d{1,2}):(\d{2})\b")
_CLOCK = re.compile(
    r"\b(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ampm>[ap]\.?m\.?)(?![a-z])"
    r"|\b(?P<h24>\d{1,2}):(?P<m24>\d{2})\b",
    re.IGNORECASE,
)
_HEDGE = re.compile(
    r"\b(about|around|roughly|approximately|circa|a bit (before|after)|just (before|after)|"
    r"shortly (before|after)|sometime)\s*$",
    re.IGNORECASE,
)
_NAMED = re.compile(r"\b(midnight|noon|midday)\b", re.IGNORECASE)
_NEXT_DAY = re.compile(r"\b(next (morning|day)|tomorrow)\b", re.IGNORECASE)
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
# "on Friday at 5 PM" -> that weekday on/after the document date. Possessives ("Friday's demo") don't count.
_WEEKDAY = re.compile(r"\bon (" + "|".join(_WEEKDAYS) + r")\b(?!')", re.IGNORECASE)
_RANGE_JOINER =re.compile(r"^\s*(-|–|to|until|till)\s+((about|around|roughly)\s+)?$", re.IGNORECASE)


@dataclass(frozen=True)
class TimeMention:
    time: datetime
    start: int
    end: int
    approximate: bool
    explicit_date: bool


@dataclass(frozen=True)
class TimeSpan:
    start: datetime
    end: datetime | None
    approximate: bool


def find_times(text: str, base_date: date) -> list[TimeMention]:
    found: list[TimeMention] = []
    taken: list[tuple[int, int]] = []

    for m in _FULL.finditer(text):
        h, mi = int(m.group(2)), int(m.group(3))
        if h > 23 or mi > 59:
            continue
        dt = datetime.combine(date.fromisoformat(m.group(1)), datetime.min.time()).replace(hour=h, minute=mi)
        found.append(TimeMention(dt, m.start(), m.end(), _hedged(text, m.start()), True))
        taken.append((m.start(), m.end()))

    day = _resolve_day(text, base_date)
    for m in _CLOCK.finditer(text):
        if any(s <= m.start() < e for s, e in taken):
            continue
        if m.group("h") is not None:
            h, mi = int(m.group("h")), int(m.group("m") or 0)
            pm = m.group("ampm").lower().startswith("p")
            if not 1 <= h <= 12:
                continue
            h = (h % 12) + (12 if pm else 0)
        else:
            h, mi = int(m.group("h24")), int(m.group("m24"))
        if h > 23 or mi > 59:
            continue
        dt = datetime.combine(day, datetime.min.time()).replace(hour=h, minute=mi)
        found.append(TimeMention(dt, m.start(), m.end(), _hedged(text, m.start()), False))

    for m in _NAMED.finditer(text):
        if m.group(1).lower() == "midnight":  # the midnight that ends the day: 00:00 the next day
            dt = datetime.combine(day + timedelta(days=1), datetime.min.time())
        else:
            dt = datetime.combine(day, datetime.min.time()).replace(hour=12)
        found.append(TimeMention(dt, m.start(), m.end(), _hedged(text, m.start()), False))

    return sorted(found, key=lambda t: t.start)


def time_span(text: str, base_date: date) -> TimeSpan | None:
    """The time a sentence is about: its first time, plus an end time if it states a range."""
    times = find_times(text, base_date)
    if not times:
        return None
    first = times[0]
    end = None
    approximate = first.approximate
    if len(times) > 1 and _RANGE_JOINER.match(text[first.end : times[1].start]):
        end = times[1].time
        approximate = approximate or times[1].approximate or bool(
            re.search(r"(about|around|roughly)\s+$", text[first.end : times[1].start], re.IGNORECASE)
        )
    return TimeSpan(first.time, end, approximate)


def _resolve_day(text: str, base_date: date) -> date:
    """Relative day words shift the default date: 'the next morning', 'tomorrow', 'on Friday'."""
    if _NEXT_DAY.search(text):
        return base_date + timedelta(days=1)
    if m := _WEEKDAY.search(text):
        target = _WEEKDAYS.index(m.group(1).lower())
        return base_date + timedelta(days=(target - base_date.weekday()) % 7)
    return base_date


def _hedged(text: str, start: int) -> bool:
    return bool(_HEDGE.search(text[max(0, start - 25) : start]))
