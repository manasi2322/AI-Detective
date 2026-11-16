"""Alibi checking: every whereabouts claim is tested against the movement records.

Verdicts, from strongest to weakest:
  SUPPORTED     a record directly confirms it (a badge exit two minutes after the claimed time)
  CONSISTENT    no record conflicts, but none can confirm it either (nobody badges into a restaurant)
  UNVERIFIED    the records say nothing either way
  CONTRADICTED  a record shows something the claim rules out

Each check keeps both sides: the claim's quote and the record quotes that decide it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .claims import Claim, ClaimType
from .models import Case, Quote
from .presence import ASSUME_COMPLETE, Movement, Presence

TOLERANCE = timedelta(minutes=10)  # people round times: "6 PM" for an 18:02 exit
TOLERANCE_APPROX = timedelta(minutes=15)  # "about", "around", "a bit before"


class Verdict(str, Enum):
    SUPPORTED = "supported"
    CONSISTENT = "consistent"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"


@dataclass
class AlibiCheck:
    claim: Claim
    verdict: Verdict
    evidence: list[Quote]
    explanation: str
    assumptions: list[str] = field(default_factory=list)


@dataclass
class Alibi:
    person: str
    checks: list[AlibiCheck]

    @property
    def status(self) -> str:
        verdicts = {c.verdict for c in self.checks}
        if not verdicts:
            return "no claims"
        if Verdict.CONTRADICTED in verdicts:
            return "broken"
        if verdicts & {Verdict.SUPPORTED, Verdict.CONSISTENT}:
            return "holds"
        return "unverified"

    @property
    def contradictions(self) -> list[AlibiCheck]:
        return [c for c in self.checks if c.verdict is Verdict.CONTRADICTED]


def _hm(t: datetime) -> str:
    return t.strftime("%H:%M")


def _cite(m: Movement) -> str:
    return f"{m.quote.cite()}"


def _claimed(c: Claim) -> str:
    return f"claimed {'~' if c.approximate else ''}{_hm(c.start)}"


class AlibiChecker:
    def __init__(self, case: Case, presence: Presence):
        self.case, self.presence = case, presence

    def check(self, claim: Claim) -> AlibiCheck:
        tol = TOLERANCE_APPROX if claim.approximate else TOLERANCE
        if claim.type in (ClaimType.DEPARTURE, ClaimType.ARRIVAL):
            return self._crossing(claim, tol)
        if claim.type in (ClaimType.NO_RETURN, ClaimType.ELSEWHERE):
            return self._away(claim, tol)
        return self._present(claim, tol)

    def _entrance(self, m: Movement) -> bool:
        loc = self.case.location(m.location)
        return bool(loc and loc.entrance)

    def _crossing(self, c: Claim, tol: timedelta) -> AlibiCheck:
        direction = "out" if c.type is ClaimType.DEPARTURE else "in"
        verb = "leaving" if direction == "out" else "entering"
        same_day = [
            m for m in self.presence.movements(c.person)
            if m.direction == direction and self._entrance(m) and m.time.date() == c.start.date()
        ]
        near = [m for m in same_day if abs(m.time - c.start) <= tol]
        if near:
            records = ", ".join(f"{_hm(m.time)} [{_cite(m)}]" for m in near)
            return AlibiCheck(c, Verdict.SUPPORTED, [m.quote for m in near],
                              f"Records show {c.person} {verb} at {records}; {_claimed(c)}.")
        if same_day:
            m = min(same_day, key=lambda m: abs(m.time - c.start))
            gap = int(abs(m.time - c.start).total_seconds() // 60)
            return AlibiCheck(c, Verdict.CONTRADICTED, [m.quote],
                              f"Claimed {verb} at {_hm(c.start)}, but the record [{_cite(m)}] shows "
                              f"{verb} at {_hm(m.time)}, {gap} minutes off.")
        return AlibiCheck(c, Verdict.UNVERIFIED, [],
                          f"No record of {c.person} {verb} the premises that day.", [ASSUME_COMPLETE])

    def _away(self, c: Claim, tol: timedelta) -> AlibiCheck:
        end = c.end or c.start
        a, b = c.start + tol, end - tol
        if b <= a:
            a, b = c.start, end
        where = "off the premises" if c.type is ClaimType.NO_RETURN else f"at {c.location}"
        seen = self.presence.between(c.person, a, b)
        stays = [s for s in self.presence.stays(c.person) if s.overlaps(a, b)]
        if seen or stays:
            quotes = list(dict.fromkeys([m.quote for m in seen] + [q for s in stays for q in s.quotes() if q]))
            detail = (
                "records put them " + ", ".join(f"at {m.location} at {_hm(m.time)} [{_cite(m)}]" for m in seen)
                if seen
                else f"records show them on the premises ({stays[0].describe()})"
            )
            return AlibiCheck(c, Verdict.CONTRADICTED, quotes,
                              f"Claims to be {where} from {_hm(c.start)} to {end.strftime('%m-%d %H:%M')}, "
                              f"but {detail}.")
        state, why = self.presence.state_at(c.person, a)
        if state == "off site":
            return AlibiCheck(c, Verdict.CONSISTENT, why,
                              f"No record places {c.person} on the premises during the claimed time "
                              f"(last seen leaving: {', '.join(q.cite() for q in why)}). "
                              f"The records cannot confirm they were {where}.",
                              [ASSUME_COMPLETE])
        return AlibiCheck(c, Verdict.UNVERIFIED, [],
                          f"No records of {c.person} around that time.", [ASSUME_COMPLETE])

    def _present(self, c: Claim, tol: timedelta) -> AlibiCheck:
        end = c.end or c.start
        at = self.presence.between(c.person, c.start - tol, end + tol, location=c.location)
        if at:
            records = ", ".join(f"{_hm(m.time)} [{_cite(m)}]" for m in at)
            return AlibiCheck(c, Verdict.SUPPORTED, [m.quote for m in at],
                              f"Records put {c.person} at {c.location} at {records}; {_claimed(c)}.")
        state, why = self.presence.state_at(c.person, c.start)
        if state == "on site":
            return AlibiCheck(c, Verdict.CONSISTENT, why,
                              f"Records put {c.person} on the premises then, but not specifically at {c.location}.")
        if state == "off site":
            return AlibiCheck(c, Verdict.CONTRADICTED, why,
                              f"Claims to be at {c.location} at {_hm(c.start)}, but records show them off the "
                              f"premises then ({', '.join(q.cite() for q in why)}).", [ASSUME_COMPLETE])
        return AlibiCheck(c, Verdict.UNVERIFIED, [], f"No records of {c.person} around {_hm(c.start)}.")


def check_alibis(case: Case, claims: list[Claim], presence: Presence) -> dict[str, Alibi]:
    checker = AlibiChecker(case, presence)
    alibis = {p.name: Alibi(p.name, []) for p in case.people}
    for claim in claims:
        alibis[claim.person].checks.append(checker.check(claim))
    return alibis
