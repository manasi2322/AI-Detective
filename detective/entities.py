"""Entity extraction: find people and locations from the case roster, with exact source spans."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .grounding import make_quote
from .models import Case, Mention
from .segments import Segment


@dataclass(frozen=True)
class Hit:
    name: str
    start: int
    end: int


class EntityMatcher:
    """Matches full names and aliases. People are case-sensitive (names); places are not."""

    def __init__(self, case: Case):
        self._people = self._build({p.name: (p.name, *p.aliases) for p in case.people}, re.UNICODE)
        self._places = self._build(
            {l.name: (l.name, *l.aliases) for l in case.locations}, re.UNICODE | re.IGNORECASE
        )

    @staticmethod
    def _build(table: dict[str, tuple[str, ...]], flags: int):
        alias_to_name: dict[str, str] = {}
        for name, aliases in table.items():
            for alias in aliases:
                key = alias if not flags & re.IGNORECASE else alias.lower()
                alias_to_name[key] = name
        # Longest alias first so "Marcus Hale" wins over "Marcus".
        ordered = sorted(alias_to_name, key=len, reverse=True)
        pattern = re.compile(r"\b(" + "|".join(re.escape(a) for a in ordered) + r")\b", flags)
        return pattern, alias_to_name, bool(flags & re.IGNORECASE)

    @staticmethod
    def _match(table, text: str) -> list[Hit]:
        pattern, alias_to_name, ci = table
        return [
            Hit(alias_to_name[m.group(1).lower() if ci else m.group(1)], m.start(), m.end())
            for m in pattern.finditer(text)
        ]

    def people(self, text: str) -> list[Hit]:
        return self._match(self._people, text)

    def places(self, text: str) -> list[Hit]:
        return self._match(self._places, text)

    @staticmethod
    def unique(hits: list[Hit]) -> list[str]:
        return list(dict.fromkeys(h.name for h in hits))


def extract_mentions(case: Case, segments: list[Segment], matcher: EntityMatcher) -> dict[str, list[Mention]]:
    """Every place a person or location is mentioned, keyed by canonical name."""
    mentions: dict[str, list[Mention]] = {p.name: [] for p in case.people}
    mentions.update({l.name: [] for l in case.locations})
    for seg in segments:
        doc = case.documents[seg.quote.doc_id]
        for kind, hits in (("person", matcher.people(seg.text)), ("location", matcher.places(seg.text))):
            for h in hits:
                q = make_quote(doc, seg.quote.start + h.start, seg.quote.start + h.end)
                mentions[h.name].append(Mention(h.name, kind, q))
    return mentions
