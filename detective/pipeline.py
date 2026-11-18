"""Wire the stages together: load -> segment -> entities -> events -> timeline + search store."""

from __future__ import annotations

from dataclasses import dataclass, field

from .alibi import Alibi, check_alibis
from .claims import Claim, extract_claims
from .entities import EntityMatcher, extract_mentions
from .events import extract_events
from .grounding import verify
from .investigator import Assessment, StepProposer, add_llm_steps, assess
from .links import CCTVMatch, Connection, find_connections, match_cctv
from .llm_extract import LLMEventExtractor, Proposer
from .models import Case, CaseIndex, Quote
from .motive import Motive, find_motives
from .opportunity import Opportunity, Window, assess_opportunity, resolve_window
from .presence import Presence
from .records import Dispute, find_disputes
from .segments import Segment, segment_document
from .speculation import Speculation, find_speculation
from .statements import StatementConflict, find_conflicts
from .store import EvidenceStore
from .timeline import Timeline


@dataclass
class Investigation:
    index: CaseIndex
    segments: list[Segment]
    matcher: EntityMatcher
    store: EvidenceStore
    timeline: Timeline
    presence: Presence
    claims: list[Claim] = field(default_factory=list)
    alibis: dict[str, Alibi] = field(default_factory=dict)
    speculation: list[Speculation] = field(default_factory=list)
    window: Window | None = None
    opportunity: dict[str, Opportunity] = field(default_factory=dict)
    disputes: list[Dispute] = field(default_factory=list)
    motives: list[Motive] = field(default_factory=list)
    cctv_matches: list[CCTVMatch] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list)
    conflicts: list[StatementConflict] = field(default_factory=list)
    assessment: Assessment | None = None

    def all_quotes(self) -> list[Quote]:
        quotes = [e.quote for e in self.index.events] + [c.quote for c in self.claims]
        quotes += [q for a in self.alibis.values() for c in a.checks + a.sightings for q in c.evidence]
        quotes += [s.quote for s in self.speculation] + [q for o in self.opportunity.values() for q in o.evidence]
        if self.window:
            quotes += [self.window.start_quote, self.window.end_quote]
        quotes += [q for d in self.disputes for q in (d.record, d.cctv)] + [m.quote for m in self.motives]
        quotes += [q for m in self.cctv_matches for q in (m.cctv, *m.records)]
        quotes += [q for c in self.connections for q in (*c.messages, *([c.denial] if c.denial else []))]
        if self.assessment:
            quotes += [q for l in self.assessment.logs.values() for s in l.steps for q in s.evidence]
        return quotes


def investigate(
    case: Case, propose: Proposer | None = None, investigator: StepProposer | None = None
) -> Investigation:
    matcher = EntityMatcher(case)
    segments = [s for doc in case.documents.values() for s in segment_document(doc)]
    index = CaseIndex(case=case)
    index.mentions = extract_mentions(case, segments, matcher)
    index.events = extract_events(case, segments, matcher)

    if propose is not None:
        llm_events, index.rejections = LLMEventExtractor(propose).extract(case, matcher)
        seen = {(e.doc_id, e.quote.start, e.time) for e in index.events}
        index.events += [e for e in llm_events if (e.doc_id, e.quote.start, e.time) not in seen]

    timeline = Timeline.build(index.events)
    records = timeline.records()
    disputes = find_disputes(case, records)
    disputed = {d.record for d in disputes}
    # Disputed badge/login lines never reach the presence model, so alibi and opportunity ignore them.
    presence = Presence(case, [e for e in records if e.quote not in disputed])
    claims = extract_claims(case, segments, matcher)
    window = resolve_window(case)
    inv = Investigation(
        index, segments, matcher, EvidenceStore(case, segments, matcher), timeline, presence,
        claims=claims,
        alibis=check_alibis(case, claims, presence),
        speculation=find_speculation(case, segments, matcher),
        window=window,
        opportunity=assess_opportunity(case, presence, window) if window else {},
        disputes=disputes,
        motives=find_motives(case, segments, matcher),
        cctv_matches=match_cctv(case, [e for e in records if e.quote not in disputed], presence),
        connections=find_connections(case, segments),
    )
    inv.conflicts = find_conflicts(case, inv.alibis)
    inv.assessment = assess(case, inv.alibis, inv.opportunity, window, inv.motives, inv.cctv_matches,
                            inv.connections, inv.speculation, inv.disputes, inv.conflicts)
    if investigator is not None:
        add_llm_steps(case, inv.assessment, investigator)

    # Final guard: nothing ungrounded leaves the pipeline.
    bad = [q.cite() for q in inv.all_quotes() if not verify(case, q)]
    if bad:
        raise AssertionError(f"ungrounded quotes produced: {bad}")
    return inv
