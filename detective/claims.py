"""Claims: what people say about their own whereabouts, turned into checkable statements.

Only first-person statements by the speaker count ("I left at 6 PM"). Interviewer questions,
statements about other people, and records are not claims. Each claim keeps its exact Quote.

Claim types:
  DEPARTURE  "I left the building at about 6:25 PM"        -> left the premises at t
  ARRIVAL    "I started my shift at 8:30 PM"               -> entered the premises at t
  NO_RETURN  "I didn't come back that night"               -> off the premises from the
             speaker's last stated departure until 06:00 the next morning
  PRESENT    "I cleaned the Design Lab at around 8:45 PM"  -> at an on-site place at t (or a range)
  ELSEWHERE  "dinner at Lantern Bistro from 7 PM to 9:30"  -> somewhere off the premises over a range
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum

from .entities import EntityMatcher
from .grounding import make_quote
from .models import Case, EvidenceKind, Quote
from .segments import Segment
from .timeparse import TimeMention, find_times, time_span


class ClaimType(str, Enum):
    DEPARTURE = "departure"
    ARRIVAL = "arrival"
    NO_RETURN = "no_return"
    PRESENT = "present"
    ELSEWHERE = "elsewhere"


@dataclass(frozen=True)
class Claim:
    id: str
    person: str
    type: ClaimType
    start: datetime
    quote: Quote
    end: datetime | None = None
    location: str | None = None
    approximate: bool = False

    def describe(self) -> str:
        t = self.start.strftime("%H:%M")
        if self.end:
            t += self.end.strftime("-%H:%M")
        where = f" {self.location}" if self.location else ""
        return f"{self.type.value}{where} {'~' if self.approximate else ''}{t}"


HOME = "home"  # pseudo-location for "at home" / "from home": always off the premises
NIGHT_ENDS = time(6, 0)  # "that night" lasts until 06:00 the next morning

_FIRST_PERSON = re.compile(r"\bI\b|\b[Mm]y\b|\b[Mm]e\b")
_NO_RETURN = re.compile(
    r"\b(?:didn'?t|did not|never)\s+(?:come|go|get|went|came|got)\s+back\b"
    r"|\b(?:didn'?t|did not|never)\s+return(?:ed)?\b",
    re.IGNORECASE,
)
_DEPART = re.compile(
    r"\b(?:left|leave|headed\s+(?:out|home|off)|went\s+(?:straight\s+)?home|walked\s+out|"
    r"clocked\s+out|signed\s+out|badged\s+out|shift\s+(?:ended|finished))\b",
    re.IGNORECASE,
)
_ARRIVE = re.compile(
    r"\b(?:arrived|arrive|got\s+(?:in|here|there|back)|came\s+(?:in|back)|returned|clocked\s+in|"
    r"signed\s+in|badged\s+in|showed\s+up|started\s+my\s+shift|shift\s+(?:started|began))\b",
    re.IGNORECASE,
)
_HOME = re.compile(r"\bhome\b", re.IGNORECASE)
_CHAT_PREFIX = re.compile(r"^\[(?P<stamp>[^\]]+)\]\s+[^:]+:\s*")


def _closest(mentions: list[TimeMention], start: int, end: int) -> TimeMention:
    return min(mentions, key=lambda t: max(t.start - end, start - t.end, 0))


def extract_claims(case: Case, segments: list[Segment], matcher: EntityMatcher) -> list[Claim]:
    claims: list[Claim] = []
    last_departure: dict[tuple[str, str], datetime] = {}
    counters: dict[str, int] = {}

    def add(seg_doc, claim_kwargs) -> None:
        key = (claim_kwargs["person"], claim_kwargs["type"], claim_kwargs["start"], claim_kwargs.get("end"))
        if any((c.person, c.type, c.start, c.end) == key and c.quote == claim_kwargs["quote"] for c in claims):
            return
        counters[seg_doc.id] = counters.get(seg_doc.id, 0) + 1
        claims.append(Claim(id=f"{seg_doc.id}#c{counters[seg_doc.id]}", **claim_kwargs))

    for seg in segments:
        doc = case.documents[seg.quote.doc_id]
        if doc.kind is EvidenceKind.RECORD or seg.role == "question" or not seg.speaker:
            continue
        if seg.speaker not in {p.name for p in case.people}:
            continue
        text, offset, base = seg.text, 0, doc.date
        if doc.type == "chat" and (m := _CHAT_PREFIX.match(text)):
            # The chat timestamp is when the message was sent, not a time the speaker is talking about.
            offset, text = m.end(), text[m.end() :]
            if stamp := re.match(r"\d{4}-\d{2}-\d{2}", m.group("stamp")):
                base = date.fromisoformat(stamp.group(0))
        if not text.strip() or text.rstrip().endswith("?") or not _FIRST_PERSON.search(text):
            continue
        quote = seg.quote if offset == 0 else make_quote(doc, seg.quote.start + offset, seg.quote.end)
        person = seg.speaker
        times = find_times(text, base)

        if nr := _NO_RETURN.search(text):
            start = _closest(times, nr.start(), nr.end()).time if times else last_departure.get((doc.id, person))
            if start is not None:
                end = datetime.combine(start.date() + timedelta(days=1), NIGHT_ENDS)
                add(doc, dict(person=person, type=ClaimType.NO_RETURN, start=start, end=end, quote=quote))
            continue
        if not times:
            continue

        moves = sorted(
            [(m, ClaimType.DEPARTURE) for m in _DEPART.finditer(text)]
            + [(m, ClaimType.ARRIVAL) for m in _ARRIVE.finditer(text)],
            key=lambda x: x[0].start(),
        )
        for m, ctype in moves:
            t = _closest(times, m.start(), m.end())
            add(doc, dict(person=person, type=ctype, start=t.time, approximate=t.approximate, quote=quote))
            if ctype is ClaimType.DEPARTURE:
                last_departure[(doc.id, person)] = t.time

        span = time_span(text, base)
        if moves and not span.end:
            continue  # "I left the office at 6 PM": the place is where they left from, not a separate claim
        places = [case.location(n) for n in matcher.unique(matcher.places(text))]
        offsite = [l.name for l in places if l and not l.onsite]
        onsite = [l.name for l in places if l and l.onsite]
        if offsite or (_HOME.search(text) and not moves):
            where, ctype = (offsite[0] if offsite else HOME), ClaimType.ELSEWHERE
        elif onsite:
            where, ctype = onsite[0], ClaimType.PRESENT
        else:
            continue
        add(
            doc,
            dict(person=person, type=ctype, start=span.start, end=span.end, location=where,
                 approximate=span.approximate, quote=quote),
        )
    return claims
