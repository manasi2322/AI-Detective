"""Disputed records: a badge swipe proves the card was used, not who used it.

If a badge (or login) record puts someone in one place, and CCTV shows that same person
somewhere else within DISPUTE_WINDOW, the badge record is marked as disputed. Disputed
records are kept out of the presence model, so they never count in alibi or opportunity checks.
CCTV wins because a camera shows a person; a reader only shows a card.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from .models import CREDENTIAL_TYPES, Case, Event, Quote

DISPUTE_WINDOW = timedelta(minutes=5)


@dataclass(frozen=True)
class Dispute:
    person: str
    record: Quote  # the badge/login line that is in doubt
    cctv: Quote  # the camera line that conflicts with it
    explanation: str


def find_disputes(case: Case, records: list[Event]) -> list[Dispute]:
    cctv = [e for e in records if case.documents[e.doc_id].type == "cctv" and e.people and e.location]
    disputes: list[Dispute] = []
    for e in records:
        if case.documents[e.doc_id].type not in CREDENTIAL_TYPES or not e.location:
            continue
        for person in e.people:
            for c in cctv:
                if person in c.people and c.location != e.location and abs(c.time - e.time) <= DISPUTE_WINDOW:
                    gap = int(abs(c.time - e.time).total_seconds() // 60)
                    disputes.append(Dispute(
                        person, e.quote, c.quote,
                        f"{person}'s credential was used at {e.location} at {e.time:%H:%M} [{e.quote.cite()}], "
                        f"but CCTV shows {person} at {c.location} {gap} min away in time [{c.quote.cite()}]. "
                        f"The card was used; who used it is in doubt.",
                    ))
                    break
    return disputes
