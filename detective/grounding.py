"""Grounding: the anti-hallucination layer.

A finding is only allowed into the system if it carries a Quote that exists verbatim
in a source document. Anything an extractor (rules or LLM) produces that cannot be
located in the evidence is rejected here.
"""

from __future__ import annotations

from .models import Case, Document, Quote


def line_of(body: str, offset: int) -> int:
    return body.count("\n", 0, offset) + 1


def make_quote(doc: Document, start: int, end: int) -> Quote:
    if not (0 <= start < end <= len(doc.body)):
        raise ValueError(f"span {start}:{end} is outside document {doc.id!r}")
    return Quote(doc.id, start, end, doc.body[start:end], line_of(doc.body, start))


def find_quote(case: Case, doc_id: str, text: str) -> Quote | None:
    """Locate `text` verbatim in a document. Returns None if it is not there."""
    doc = case.documents.get(doc_id)
    if doc is None or not text or not text.strip():
        return None
    start = doc.body.find(text)
    if start < 0:
        return None
    return make_quote(doc, start, start + len(text))


def verify(case: Case, quote: Quote) -> bool:
    """True if the quote really is the text at that position in that document."""
    doc = case.documents.get(quote.doc_id)
    return (
        doc is not None
        and 0 <= quote.start < quote.end <= len(doc.body)
        and doc.body[quote.start : quote.end] == quote.text
    )
