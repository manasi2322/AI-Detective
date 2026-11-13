"""Split documents into citable segments (sentences or log lines) with speaker information."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .grounding import make_quote
from .models import Document, Quote

# One segment per line for structured logs and chats: the timestamp lives at the start of the line.
LINE_TYPES = frozenset({"badge_log", "cctv", "chat"})

_CHAT_LINE = re.compile(r"^\[[^\]]+\]\s+(?P<speaker>[^:]+):")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])")
_PREFIX = re.compile(r"^(?P<tag>Q|A):\s*")


@dataclass(frozen=True)
class Segment:
    quote: Quote
    role: str  # "question" | "answer" | "line" | "text"
    speaker: str | None  # who is speaking, when the format tells us

    @property
    def text(self) -> str:
        return self.quote.text


def segment_document(doc: Document) -> list[Segment]:
    segments: list[Segment] = []
    offset = 0
    for raw_line in doc.body.splitlines(keepends=True):
        line_start = offset
        offset += len(raw_line)
        line = raw_line.rstrip("\r\n")
        stripped = line.strip()
        if not stripped:
            continue
        lead = len(line) - len(line.lstrip())
        start = line_start + lead
        end = line_start + len(line.rstrip())

        if doc.type in LINE_TYPES:
            speaker = None
            if doc.type == "chat" and (m := _CHAT_LINE.match(stripped)):
                speaker = m.group("speaker").strip()
            segments.append(Segment(make_quote(doc, start, end), "line", speaker))
            continue

        role, speaker = "text", doc.author
        if doc.type == "interview" and (m := _PREFIX.match(stripped)):
            role = "question" if m.group("tag") == "Q" else "answer"
            speaker = None if role == "question" else doc.author
            start += m.end()
        segments.extend(_sentences(doc, start, end, role, speaker))
    return segments


def _sentences(doc: Document, start: int, end: int, role: str, speaker: str | None) -> list[Segment]:
    text = doc.body[start:end]
    out: list[Segment] = []
    cursor = 0
    for m in _SENTENCE_END.finditer(text):
        out.append(Segment(make_quote(doc, start + cursor, start + m.start()), role, speaker))
        cursor = m.end()
    if cursor < len(text):
        out.append(Segment(make_quote(doc, start + cursor, end), role, speaker))
    return out
