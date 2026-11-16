"""Speculation: guesses and impressions are flagged so they are never treated as evidence.

"Honestly, it was probably Lena." is an opinion about Lena, not a fact about her. Flagged
statements are reported with who said them and who they are about, and nothing downstream
(alibis, opportunity) uses them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .entities import EntityMatcher
from .models import Case, EvidenceKind, Quote
from .segments import Segment

_MARKERS = re.compile(
    r"\b(probably|maybe|perhaps|possibly|likely|must have|might have|could have|may have|"
    r"I think|I bet|I guess|I suspect|I reckon|I assume|I'd say|my guess|"
    r"seem(?:s|ed)?|looked like|looks like)\b",
    re.IGNORECASE,
)
_IMPRESSION = re.compile(r"^(seem|looked like|looks like)", re.IGNORECASE)


@dataclass(frozen=True)
class Speculation:
    speaker: str | None
    about: tuple[str, ...]  # people the guess is about (never the speaker)
    marker: str
    category: str  # "guess" | "impression"
    quote: Quote


def find_speculation(case: Case, segments: list[Segment], matcher: EntityMatcher) -> list[Speculation]:
    found: list[Speculation] = []
    for seg in segments:
        doc = case.documents[seg.quote.doc_id]
        if doc.kind is EvidenceKind.RECORD or seg.role == "question":
            continue
        m = _MARKERS.search(seg.text)
        if not m:
            continue
        about = tuple(n for n in matcher.unique(matcher.people(seg.text)) if n != seg.speaker)
        category = "impression" if _IMPRESSION.match(m.group(1)) else "guess"
        found.append(Speculation(seg.speaker, about, m.group(1), category, seg.quote))
    return found
