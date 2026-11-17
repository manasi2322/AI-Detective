"""Links between evidence that no single document states.

1. CCTV matches. An unnamed person on camera ("a man in a grey hoodie") is matched to someone
   only if exactly one person has a (non-disputed) record within MATCH_WINDOW of the sighting.
   A match is always an ASSUMPTION: timing makes it likely, it does not identify anyone. A later
   line that refers back ("the same grey-hoodie figure") inherits the earlier match.

2. Hidden connections. A suspect and an outside party (a recruiter, a buyer) who appear together
   in a chat or email are connected. If the suspect also denied any contact in an interview,
   the denial is reported next to the messages that contradict it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta

from .claims import _FIRST_PERSON
from .models import Case, Event, Quote
from .presence import Presence
from .segments import Segment

MATCH_WINDOW = timedelta(minutes=5)

_REFERS_BACK = re.compile(r"\b(the same|the (?:person|figure|man|woman|individual) in)\b", re.I)
_DENIAL = re.compile(
    r"\b(?:never|haven't|have not|don't|do not|didn't|did not)\b[^.]*?"
    r"\b(?:talk(?:ed)?|spoke|spoken|met|meet|contact(?:ed)?|know|knew|been in touch|heard of)\b",
    re.I,
)
_TO_LINE = re.compile(r"^(To|Cc):", re.I)


@dataclass
class CCTVMatch:
    cctv: Quote
    person: str | None  # None when nobody, or more than one person, fits
    candidates: list[str]
    records: list[Quote]  # the records that put the candidate nearby
    refers_to: Quote | None = None  # earlier sighting this line refers back to
    label: str = "assumption"

    def explanation(self) -> str:
        if self.refers_to is not None:
            return (f"This line refers back to [{self.refers_to.cite()}], which was matched to "
                    f"{self.person}. Assumed to be the same person.")
        if self.person:
            recs = ", ".join(q.cite() for q in self.records)
            return (f"Only {self.person} has a record within {MATCH_WINDOW.seconds // 60} min of this "
                    f"sighting ({recs}). Assumed, not identified: the face is not described.")
        if self.candidates:
            return f"Several people were nearby ({', '.join(self.candidates)}): no match."
        return "Nobody has a record near this sighting: no match."


@dataclass
class Connection:
    suspect: str
    party: str
    doc_id: str
    messages: list[Quote]  # first message from each side
    denial: Quote | None = None
    label: str = "claim"
    notes: list[str] = field(default_factory=list)

    def explanation(self) -> str:
        text = f"{self.suspect} and outside party {self.party} exchange messages in {self.doc_id}."
        if self.denial:
            text += f" {self.suspect} denied any such contact [{self.denial.cite()}]."
        return text


def match_cctv(case: Case, records: list[Event], presence: Presence) -> list[CCTVMatch]:
    matches: list[CCTVMatch] = []
    last_by_doc: dict[str, CCTVMatch] = {}
    for e in records:
        if case.documents[e.doc_id].type != "cctv" or e.people:
            continue
        prev = last_by_doc.get(e.doc_id)
        if _REFERS_BACK.search(e.quote.text) and prev is not None and prev.person:
            m = CCTVMatch(e.quote, prev.person, [prev.person], prev.records, refers_to=prev.cctv)
        else:
            near: dict[str, list[Quote]] = {}
            for p in case.people:
                for mv in presence.movements(p.name):
                    if abs(mv.time - e.time) <= MATCH_WINDOW and mv.quote != e.quote:
                        near.setdefault(p.name, []).append(mv.quote)
            names = sorted(near)
            only = names[0] if len(names) == 1 else None
            m = CCTVMatch(e.quote, only, names, near.get(only, []) if only else [])
        matches.append(m)
        last_by_doc[e.doc_id] = m
    return matches


def find_connections(case: Case, segments: list[Segment]) -> list[Connection]:
    suspects = {p.name for p in case.suspects}
    outside = {p.name for p in case.people if p.outside}
    if not outside:
        return []
    first_msg: dict[str, dict[str, Quote]] = {}
    for seg in segments:
        doc = case.documents[seg.quote.doc_id]
        if doc.type not in ("chat", "email"):
            continue
        who = {seg.speaker} if seg.speaker else set()
        if doc.type == "email" and _TO_LINE.match(seg.text):
            who |= {p.name for p in case.people if p.name in seg.text}
        for name in who:
            first_msg.setdefault(doc.id, {}).setdefault(name, seg.quote)

    denials: dict[str, Quote] = {}
    for seg in segments:
        doc = case.documents[seg.quote.doc_id]
        if (doc.type == "interview" and seg.role == "answer" and seg.speaker in suspects
                and _FIRST_PERSON.search(seg.text) and _DENIAL.search(seg.text)):
            denials.setdefault(seg.speaker, seg.quote)

    out: list[Connection] = []
    for doc_id, people in first_msg.items():
        for s in sorted(suspects & people.keys()):
            for party in sorted(outside & people.keys()):
                out.append(Connection(s, party, doc_id, [people[party], people[s]], denials.get(s)))
    return out
