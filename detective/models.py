"""Core data structures. Every finding points back to a Quote: an exact span of a source document."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class EvidenceKind(str, Enum):
    """How much a piece of evidence can be trusted on its own.

    RECORD: machine logs or official records (badge log, CCTV, case brief).
    CLAIM:  what a person says (interviews, chats, emails, notices). Claims may be lies.
    """

    RECORD = "record"
    CLAIM = "claim"


RECORD_TYPES = frozenset({"badge_log", "cctv", "brief"})


@dataclass(frozen=True)
class Document:
    id: str
    type: str
    title: str
    date: date  # default date for times mentioned without one
    body: str
    path: str
    author: str | None = None

    @property
    def kind(self) -> EvidenceKind:
        return EvidenceKind.RECORD if self.type in RECORD_TYPES else EvidenceKind.CLAIM


@dataclass(frozen=True)
class Quote:
    """An exact, verifiable span of a document body: body[start:end] == text."""

    doc_id: str
    start: int
    end: int
    text: str
    line: int

    def cite(self) -> str:
        return f"{self.doc_id}:L{self.line}"


@dataclass(frozen=True)
class Person:
    name: str
    role: str
    suspect: bool
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Location:
    name: str
    aliases: tuple[str, ...] = ()


@dataclass
class Case:
    id: str
    title: str
    difficulty: str
    incident_date: date
    summary: str
    people: list[Person]
    locations: list[Location]
    documents: dict[str, Document]
    root: str

    @property
    def suspects(self) -> list[Person]:
        return [p for p in self.people if p.suspect]


@dataclass(frozen=True)
class Mention:
    entity: str
    entity_type: str  # "person" | "location"
    quote: Quote


@dataclass(frozen=True)
class Event:
    """Something that happened (or is claimed to have happened) at a point in time."""

    id: str
    time: datetime
    kind: EvidenceKind
    quote: Quote
    actor: str | None = None
    location: str | None = None
    people: tuple[str, ...] = ()
    end_time: datetime | None = None
    approximate: bool = False
    source: str = "rules"  # which extractor produced it: "rules" | "llm"

    @property
    def doc_id(self) -> str:
        return self.quote.doc_id


@dataclass
class Rejection:
    """An extracted item that was thrown away because it could not be grounded in the evidence."""

    doc_id: str
    item: dict
    reason: str


@dataclass
class CaseIndex:
    """Everything extracted from a case, ready to be searched and reasoned over."""

    case: Case
    mentions: dict[str, list[Mention]] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)
