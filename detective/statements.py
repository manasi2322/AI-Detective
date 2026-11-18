"""Conflicts between statements: two accounts of where the same person was that cannot both be true.

"Victor was with me at my flat from 8 PM until midnight" (Celia) and "Around 9:05 PM I saw
Victor near the side door" (Ben) overlap in time but put Victor in two places, one of them off
the premises. Each conflict is reported with both quotes and, where the records can tell, which
side they back.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .alibi import Alibi, AlibiCheck, Verdict
from .claims import Claim, ClaimType
from .models import Case

_PLACED = (ClaimType.PRESENT, ClaimType.ELSEWHERE)
_SLACK = timedelta(minutes=10)


@dataclass
class StatementConflict:
    person: str
    a: AlibiCheck
    b: AlibiCheck

    @property
    def backed(self) -> AlibiCheck | None:
        """The side the records support, if exactly one side is contradicted."""
        bad = [c for c in (self.a, self.b) if c.verdict is Verdict.CONTRADICTED]
        return next((c for c in (self.a, self.b) if c not in bad), None) if len(bad) == 1 else None

    def explanation(self) -> str:
        def who(c: Claim) -> str:
            return c.reported_by or c.person

        def says(c: Claim) -> str:
            subject = "they were" if c.reported_by is None else f"{self.person} was"
            speaker = f"{c.person} says" if c.reported_by is None else f"{c.reported_by} says"
            return f"{speaker} {subject} at {c.location} ({c.describe()}) [{c.quote.cite()}]"

        a, b = self.a.claim, self.b.claim
        text = f"{says(a)}, but {says(b)}."
        if self.backed is not None:
            loser = self.a if self.backed is self.b else self.b
            text += (f" The records back {who(self.backed.claim)}: {who(loser.claim)}'s account is contradicted "
                     f"by {', '.join(q.cite() for q in loser.evidence)}.")
        else:
            text += " The records do not settle it."
        return text


def _span(c: Claim) -> tuple[datetime, datetime]:
    return c.start - _SLACK, (c.end or c.start) + _SLACK


def find_conflicts(case: Case, alibis: dict[str, Alibi]) -> list[StatementConflict]:
    out: list[StatementConflict] = []
    for person, alibi in alibis.items():
        checks = [c for c in alibi.checks + alibi.sightings if c.claim.type in _PLACED and c.claim.location]
        for i, x in enumerate(checks):
            for y in checks[i + 1:]:
                cx, cy = x.claim, y.claim
                if (cx.reported_by or cx.person) == (cy.reported_by or cy.person):
                    continue  # one person's own account is not a conflict between witnesses
                (a1, a2), (b1, b2) = _span(cx), _span(cy)
                if not (a1 <= b2 and b1 <= a2) or cx.location == cy.location:
                    continue
                lx, ly = case.location(cx.location), case.location(cy.location)
                onsite_x = lx.onsite if lx else False
                onsite_y = ly.onsite if ly else False
                if onsite_x and onsite_y:
                    continue  # two places on the premises: they could have walked between them
                out.append(StatementConflict(person, x, y))
    return out
