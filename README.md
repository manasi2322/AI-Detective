# AI Detective

An AI detective that solves fictional mysteries from a case file of witness interviews, chats,
emails, CCTV summaries and access logs. It is built to reason from evidence, not to guess:
every finding is tied to an exact quote from a source document, and anything that cannot be
found in the evidence is rejected.

## Status: milestone 1 of 5 (~20%), the evidence foundation

Done:
- **Case 1, "The Missing Prototype Laptop"** (easy): 11 documents, 4 suspects, a known
  solution (`solution.json`), a lying suspect, a speculative accusation, a red-herring motive
  and an irrelevant document.
- **Structured extraction** of people, places and timed events (with aliases, hedged times like
  "about 9:30 PM", ranges, and relative days like "the next morning").
- **Searchable evidence store** (BM25) with person and document-type filters.
- **Timeline** that separates hard **records** (badge log, CCTV, case brief) from witness
  **claims** (interviews, chats, emails).
- **Grounding**: every event and mention carries a `Quote` (document, character span, line).
  An LLM extractor is included, and every proposal it makes is checked against the source
  before it is accepted.
- **22 automated tests** against the case's known facts.

Next: contradiction detection (e.g. an alibi that conflicts with the badge log).

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pytest
pytest -q                                   # 22 passed

python -m detective timeline cases/case1_missing_laptop
python -m detective timeline cases/case1_missing_laptop --records
python -m detective timeline cases/case1_missing_laptop --person "Marcus Hale"
python -m detective search   cases/case1_missing_laptop "laptop drawer"
python -m detective entities cases/case1_missing_laptop
```

Example timeline rows:

```
2026-03-12 18:00        CLAIM   Marcus Hale @ Brightwave Office
                               "I left the office at 6 PM and went straight home."  [interview_marcus:L2]
2026-03-12 19:44        RECORD  Marcus Hale @ Design Lab
                               "2026-03-12 19:44 | Marcus Hale | Design Lab | ENTRY"  [badge_log:L7]
```

### Optional: Claude-assisted extraction

```bash
pip install anthropic pydantic
export ANTHROPIC_API_KEY=...               # or: ant auth login
python -m detective timeline cases/case1_missing_laptop --llm
```

Claude (`claude-opus-5-5`) proposes extra events from each document. Server-side refusal
fallback is enabled. Each proposal is accepted only if:
1. its quote appears **verbatim** in the document,
2. the time it gives is **actually stated** in that quote,
3. its actor is a known person who is **named in the quote or is its speaker**,
4. its location is a known place **named in the quote**.

Rejected proposals are listed with the reason, so hallucinations are visible rather than silent.

## Architecture

```
cases/<case>/case.json        cast list, places, incident date
cases/<case>/documents/*.txt  evidence, each with front matter (id, type, date, author)
cases/<case>/solution.json    answer key: read only by tests, never by the pipeline

detective/
  loader.py            parse case folder + front matter
  segments.py          split documents into citable sentences / log lines, track speakers
  grounding.py         Quote creation + verification (the anti-hallucination layer)
  timeparse.py         clock times, hedges, ranges, relative days
  entities.py          roster/alias matching for people and places
  events.py            rule-based timed-event extraction
  llm_extract.py       LLM proposals -> validated Events or Rejections
  anthropic_backend.py Claude call with structured output (lazy import)
  store.py             BM25 evidence search
  timeline.py          ordering, record/claim split, per-person views, rendering
  pipeline.py          wires it together; final check that every event is grounded
  cli.py               command-line explorer
```

Design choices:
- **Records vs. claims** is decided by document type, not by the LLM, so a confident witness
  can never be promoted to a fact.
- **Rules first, LLM second.** Rule-based extraction gives a deterministic, testable baseline;
  the LLM adds coverage on messy prose, behind the same grounding checks.
- **The model never sees the answer key.** `solution.json` is used only for evaluation.

## Roadmap

| Milestone | Scope |
|---|---|
| 1 (done) | Case 1, extraction, search, timeline, grounding, tests |
| 2 | Contradiction detection (alibi vs. badge/CCTV), speculation flagging, opportunity matrix |
| 3 | Motive analysis, LLM investigator that weighs findings, confidence levels |
| 4 | Cases 2 and 3 (twisted / impossible), follow-up questions, new-evidence reassessment |
| 5 | Final case reports, evaluation harness across all cases |
