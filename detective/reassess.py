"""Reassessment: re-run the investigation after new evidence and show what changed.

Two ways evidence arrives:
  - uncovered: a case's later stages (`stage: 2` documents), e.g. CCTV requested on day 2;
  - added: a document the investigator brings in (`add-evidence`, `:add` in chat, the web UI).
Either way the whole pipeline runs again from scratch, so nothing from the earlier run is reused,
and `compare` lists how the ranking, confidence and each suspect's reasoning changed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .investigator import Step
from .models import Document


@dataclass
class SuspectChange:
    suspect: str
    before: float
    after: float
    gone: list[Step] = field(default_factory=list)
    new: list[Step] = field(default_factory=list)

    @property
    def delta(self) -> float:
        return round(self.after - self.before, 2)


@dataclass
class Comparison:
    added: list[Document]
    leader_before: str
    leader_after: str
    confidence_before: str
    confidence_after: str
    changes: list[SuspectChange]
    new_disputes: list = field(default_factory=list)
    new_contradictions: list[str] = field(default_factory=list)

    @property
    def leader_changed(self) -> bool:
        return self.leader_before != self.leader_after

    def render(self) -> str:
        out = [f"New evidence ({len(self.added)} document{'s' if len(self.added) != 1 else ''}):"]
        out += [f"  + {d.id} ({d.type}): {d.title}" for d in self.added]
        if self.leader_changed:
            out.append(f"\nThe conclusion CHANGED: {self.leader_before} ({self.confidence_before}) -> "
                       f"{self.leader_after} ({self.confidence_after}).")
        else:
            out.append(f"\nThe conclusion holds: {self.leader_after} "
                       f"(confidence {self.confidence_before} -> {self.confidence_after}).")
        out.append("\n  Suspect              before   after   change")
        for c in sorted(self.changes, key=lambda c: -c.after):
            out.append(f"  {c.suspect:<20} {c.before:+6.1f}  {c.after:+6.1f}  {c.delta:+6.1f}")
        for c in self.changes:
            if c.gone or c.new:
                out.append(f"\n  {c.suspect}:")
                out += [f"    - no longer counted ({s.weight:+.1f}): {s.text}" for s in c.gone]
                out += [f"    + new ({s.weight:+.1f}): {s.text}" for s in c.new]
        for d in self.new_disputes:
            out.append(f"\n  Newly disputed record: {d.explanation}")
        for x in self.new_contradictions:
            out.append(f"\n  New contradiction: {x}")
        return "\n".join(out)


def compare(before, after) -> Comparison:
    old, new = before.assessment, after.assessment
    added = [d for d in after.index.case.documents.values() if d.id not in before.index.case.documents]
    changes = []
    for name in new.logs:
        b = old.logs.get(name)
        before_texts = {s.text for s in b.steps} if b else set()
        after_texts = {s.text for s in new.logs[name].steps}
        changes.append(SuspectChange(
            name, b.score if b else 0.0, new.logs[name].score,
            [s for s in (b.steps if b else []) if s.text not in after_texts and s.weight != 0],
            [s for s in new.logs[name].steps if s.text not in before_texts and s.weight != 0],
        ))
    old_disputes = {d.record for d in before.disputes}

    def contradictions(inv) -> set[str]:
        out = {c.explanation for a in inv.alibis.values() for c in a.checks + a.sightings if c.verdict.value == "contradicted"}
        out |= {c.explanation() for c in inv.conflicts}
        out |= {c.explanation() for c in inv.connections if c.denial}
        return out

    return Comparison(
        added=added,
        leader_before=old.most_likely, leader_after=new.most_likely,
        confidence_before=old.confidence()[0], confidence_after=new.confidence()[0],
        changes=changes,
        new_disputes=[d for d in after.disputes if d.record not in old_disputes],
        new_contradictions=sorted(contradictions(after) - contradictions(before)),
    )
