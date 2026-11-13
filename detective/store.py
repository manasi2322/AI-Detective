"""Searchable evidence store: BM25 ranking over citable segments, with person / type filters.

Pure Python and deterministic, so retrieval quality can be tested exactly. Each hit is a
Quote, so whatever the investigator (or later the LLM) reads is already citable.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .entities import EntityMatcher
from .models import Case, Quote
from .segments import Segment

_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    "a an and are as at be but by did do for from had has have he her his i in is it its me my "
    "no not of on or our she so that the their them then there they this to was we were what "
    "when where who why will with you your".split()
)


def tokenize(text: str) -> list[str]:
    return [_stem(w) for w in _WORD.findall(text.lower()) if w not in _STOP]


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


@dataclass(frozen=True)
class Passage:
    quote: Quote
    doc_type: str
    people: frozenset[str]
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class SearchHit:
    quote: Quote
    score: float
    doc_type: str


class EvidenceStore:
    def __init__(self, case: Case, segments: list[Segment], matcher: EntityMatcher, k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.passages: list[Passage] = []
        for seg in segments:
            doc = case.documents[seg.quote.doc_id]
            people = set(matcher.unique(matcher.people(seg.text)))
            if seg.speaker:
                people.add(seg.speaker)
            self.passages.append(Passage(seg.quote, doc.type, frozenset(people), tuple(tokenize(seg.text))))
        self._tf = [Counter(p.tokens) for p in self.passages]
        self._avg_len = sum(len(p.tokens) for p in self.passages) / max(1, len(self.passages))
        df: Counter[str] = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(self.passages)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(
        self,
        query: str,
        k: int = 5,
        person: str | None = None,
        doc_types: set[str] | None = None,
    ) -> list[SearchHit]:
        terms = tokenize(query)
        hits: list[SearchHit] = []
        for passage, tf in zip(self.passages, self._tf):
            if person and person not in passage.people:
                continue
            if doc_types and passage.doc_type not in doc_types:
                continue
            score = self._bm25(terms, tf, len(passage.tokens))
            if score > 0 or (not terms and (person or doc_types)):
                hits.append(SearchHit(passage.quote, score, passage.doc_type))
        hits.sort(key=lambda h: (-h.score, h.quote.doc_id, h.quote.start))
        return hits[:k]

    def _bm25(self, terms: list[str], tf: Counter[str], length: int) -> float:
        score = 0.0
        for t in terms:
            f = tf.get(t, 0)
            if f:
                norm = f + self.k1 * (1 - self.b + self.b * length / self._avg_len)
                score += self._idf[t] * f * (self.k1 + 1) / norm
        return score
