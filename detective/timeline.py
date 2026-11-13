"""Timeline: all events in time order, with hard records kept apart from witness claims."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import Event, EvidenceKind


@dataclass
class Timeline:
    events: list[Event]

    @classmethod
    def build(cls, events: list[Event]) -> "Timeline":
        # Records sort before claims at the same minute: the log is the reference point.
        order = {EvidenceKind.RECORD: 0, EvidenceKind.CLAIM: 1}
        return cls(sorted(events, key=lambda e: (e.time, order[e.kind], e.doc_id, e.quote.start)))

    def records(self) -> list[Event]:
        return [e for e in self.events if e.kind is EvidenceKind.RECORD]

    def claims(self) -> list[Event]:
        return [e for e in self.events if e.kind is EvidenceKind.CLAIM]

    def for_person(self, name: str) -> list[Event]:
        return [e for e in self.events if e.actor == name or name in e.people]

    def between(self, start: datetime, end: datetime) -> list[Event]:
        return [e for e in self.events if start <= e.time <= end]

    def render(self, kinds: set[EvidenceKind] | None = None) -> str:
        rows = []
        for e in self.events:
            if kinds and e.kind not in kinds:
                continue
            when = e.time.strftime("%Y-%m-%d %H:%M")
            if e.end_time:
                when += e.end_time.strftime("-%H:%M")
            if e.approximate:
                when = "~" + when
            who = e.actor or "(unidentified)"
            where = f" @ {e.location}" if e.location else ""
            rows.append(
                f"{when:<23} {e.kind.value.upper():<6}  {who}{where}\n"
                f"{'':<31}\"{e.quote.text}\"  [{e.quote.cite()}]"
            )
        return "\n".join(rows)
