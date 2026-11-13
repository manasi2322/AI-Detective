"""Wire the stages together: load -> segment -> entities -> events -> timeline + search store."""

from __future__ import annotations

from dataclasses import dataclass

from .entities import EntityMatcher, extract_mentions
from .events import extract_events
from .grounding import verify
from .llm_extract import LLMEventExtractor, Proposer
from .models import Case, CaseIndex
from .segments import Segment, segment_document
from .store import EvidenceStore
from .timeline import Timeline


@dataclass
class Investigation:
    index: CaseIndex
    segments: list[Segment]
    matcher: EntityMatcher
    store: EvidenceStore
    timeline: Timeline


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

    # Final guard: nothing ungrounded leaves the pipeline.
    bad = [e.id for e in index.events if not verify(case, e.quote)]
    if bad:
        raise AssertionError(f"ungrounded events produced: {bad}")

    return Investigation(index, segments, matcher, EvidenceStore(case, segments, matcher), Timeline.build(index.events))
