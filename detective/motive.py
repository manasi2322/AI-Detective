"""Motive detection: statements that give someone a reason to act.

Types (with the evidence each needs):
  GAIN      someone offers or promises a reward for the item ("can make you an offer ... prototype")
  INTENT    a stated plan to take the item ("I'll grab the laptop")
  MONEY     money trouble ("I need the money before my visa fee is due")
  CONFLICT  a clash or refusal ("he said no", "we argued")
  NEED      the person themselves says they want or need the item ("could I borrow the laptop")

Whose motive it is: in a chat, "you" means the other person in the chat; otherwise a
first-person statement belongs to the speaker; otherwise the person named in it. Each motive
records whether the person said it themselves or someone else reported it.

Guesses and impressions ("probably", "seemed stressed about money") are never motives: they
are flagged by speculation.py and skipped here. Interviewer questions are skipped too.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .claims import _CHAT_PREFIX, _FIRST_PERSON
from .entities import EntityMatcher
from .models import Case, EvidenceKind, Quote
from .segments import Segment
from .speculation import _MARKERS as _SPECULATION


class MotiveType(str, Enum):
    GAIN = "gain"
    INTENT = "intent"
    MONEY = "money"
    CONFLICT = "conflict"
    NEED = "need"


_PATTERNS = {
    MotiveType.GAIN: re.compile(r"\b(offer|reward|bonus|buyer|sell|sold|pay you|paid|job)\b", re.I),
    MotiveType.INTENT: re.compile(
        r"\bI(?:'ll| will|'m going to| am going to| plan to)\s+(?:take|get|grab|steal|bring|swipe)\b", re.I
    ),
    MotiveType.MONEY: re.compile(
        r"\b(debts?|owe[sd]?|broke|money|rent|loans?|bills|fees?|can't afford|cannot afford)\b", re.I
    ),
    MotiveType.CONFLICT: re.compile(
        r"\b(argued|argument|fight|fought|furious|angry|grudge|hated?|threatened|fired|passed over|"
        r"said no|refused|turned (?:me|him|her|us) down)\b",
        re.I,
    ),
    MotiveType.NEED: re.compile(r"\b(need(?:s|ed)?|want(?:s|ed)?|borrow|lend)\b", re.I),
}
# Types that only count when the item itself is mentioned (an offer for *what*?).
_NEEDS_ITEM = {MotiveType.GAIN, MotiveType.INTENT, MotiveType.NEED}
_SECOND_PERSON = re.compile(r"\b(you|your)\b", re.I)


@dataclass(frozen=True)
class Motive:
    person: str
    type: MotiveType
    quote: Quote
    reported_by: str | None
    self_reported: bool
    trigger: str

    def describe(self) -> str:
        who = "said it themselves" if self.self_reported else f"reported by {self.reported_by or 'unknown'}"
        return f"{self.type.value} ({who}): \"{self.trigger}\""


def find_motives(case: Case, segments: list[Segment], matcher: EntityMatcher) -> list[Motive]:
    item = re.compile(r"\b(" + "|".join(re.escape(a) for a in case.item) + r")\b", re.I) if case.item else None
    known = {p.name for p in case.people}
    chat_people: dict[str, list[str]] = {}
    for seg in segments:
        if case.documents[seg.quote.doc_id].type == "chat" and seg.speaker in known:
            chat_people.setdefault(seg.quote.doc_id, [])
            if seg.speaker not in chat_people[seg.quote.doc_id]:
                chat_people[seg.quote.doc_id].append(seg.speaker)

    found: list[Motive] = []
    for seg in segments:
        doc = case.documents[seg.quote.doc_id]
        if doc.kind is EvidenceKind.RECORD or seg.role == "question":
            continue
        text = seg.text
        if doc.type == "chat" and (m := _CHAT_PREFIX.match(text)):
            text = text[m.end() :]
        if _SPECULATION.search(text):
            continue  # a guess is not a motive
        mentions_item = bool(item and item.search(text))
        first_person = bool(_FIRST_PERSON.search(text))

        # Whose motive is it?
        others = [p for p in chat_people.get(doc.id, []) if p != seg.speaker]
        if doc.type == "chat" and _SECOND_PERSON.search(text) and len(others) == 1:
            owner = others[0]
        elif first_person and seg.speaker in known:
            owner = seg.speaker
        else:
            named = [n for n in matcher.unique(matcher.people(text)) if n != seg.speaker]
            owner = named[0] if named else None
        if owner is None:
            continue

        for mtype, pattern in _PATTERNS.items():
            m = pattern.search(text)
            if not m or (mtype in _NEEDS_ITEM and not mentions_item):
                continue
            if mtype is MotiveType.NEED and not (first_person and owner == seg.speaker):
                continue  # only the person themselves can tell us what they want
            found.append(Motive(owner, mtype, seg.quote, seg.speaker, owner == seg.speaker, m.group(0)))
    return found
