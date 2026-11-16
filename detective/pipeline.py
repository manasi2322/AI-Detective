"""Wire the stages together: load -> segment -> entities -> events -> timeline + search store."""

from __future__ import annotations

from dataclasses import dataclass, field

from .alibi import Alibi, check_alibis
from .claims import Claim, extract_claims
from .entities import EntityMatcher, extract_mentions
from .events import extract_events
from .grounding import verify
from .llm_extract import LLMEventExtractor, Proposer
from .models import Case, CaseIndex, Quote
from .opportunity import Opportunity, Window, assess_opportunity, resolve_window
from .presence import Presence
from .segments import Segment, segment_document
from .speculation import Speculation, find_speculation
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

    def all_quotes(self) -> list[Quote]:
        quotes = [e.quote for e in self.index.events] + [c.quote for c in self.claims]
        quotes += [q for a in self.alibis.values() for c in a.checks for q in c.evidence]
        quotes += [s.quote for s in self.speculation] + [q for o in self.opportunity.values() for q in o.evidence]
        if self.window:
            quotes += [self.window.start_quote, self.window.end_quote]
        return quotes


def investigate(case: Case, propose: Proposer | None = None) -> Investigation:
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
    presence = Presence(case, timeline.records())
    claims = extract_claims(case, segments, matcher)
    window = resolve_window(case)
    inv = Investigation(
        index, segments, matcher, EvidenceStore(case, segments, matcher), timeline, presence,
        claims=claims,
        alibis=check_alibis(case, claims, presence),
        speculation=find_speculation(case, segments, matcher),
        window=window,
        opportunity=assess_opportunity(case, presence, window) if window else {},
    )

    # Final guard: nothing ungrounded leaves the pipeline.
    bad = [q.cite() for q in inv.all_quotes() if not verify(case, q)]
    if bad:
        raise AssertionError(f"ungrounded quotes produced: {bad}")
    return inv
