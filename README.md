# AI Detective

An AI detective that solves fictional mysteries from a case file of witness interviews, chats,
emails, CCTV summaries and access logs. It is built to reason from evidence, not to guess:
every finding is tied to an exact quote from a source document, and anything that cannot be
found in the evidence is rejected.

## Progress

| Milestone | Scope | Status | Tests |
|---|---|---|---|
| 1 | Evidence foundation: Case 1, extraction, search, timeline, grounding | Done (~20%) | 22 |
| 2 | Alibi checking, speculation flags, opportunity, holdout case | Done (~35%) | 28 |
| 3 | Motive analysis, LLM investigator that weighs findings, confidence levels | Next | |
| 4 | Cases 2 and 3 (twisted / impossible), follow-up questions, new-evidence reassessment | Planned | |
| 5 | Final case reports, evaluation harness across all cases | Planned | |

**Total: 50 automated tests, all passing.**

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pytest
pytest -q                                   # 50 passed
```

---

## Milestone 1: the evidence foundation (~20%)

The system can read a case file, pull out who, where and when, search the evidence, and lay
everything out on a timeline, and it rejects anything that isn't in the documents.

### What was built

- **Case 1, "The Missing Prototype Laptop"** (easy): 11 documents (interviews, badge log,
  CCTV summary, a recovered chat, an email, a case brief, an irrelevant notice), 4 suspects and
  a known solution in `solution.json`. The case includes a lying suspect, a speculative
  accusation, a red-herring motive and an irrelevant document.
- **Structured extraction** of people, places and timed events. It handles aliases ("Marcus"
  means Marcus Hale), hedged times ("about 9:30 PM"), ranges ("from 7 PM to 8 PM") and relative
  days ("the next morning").
- **Searchable evidence store** (BM25) with person and document-type filters. Every search hit
  is a citable quote.
- **Timeline** that keeps hard **records** (badge log, CCTV, case brief) separate from witness
  **claims** (interviews, chats, emails). Records come first when both happen at the same minute.
- **Grounding (anti-hallucination).** Every event and mention carries a `Quote`: the document,
  the exact character span and the line number. Nothing leaves the pipeline unless its quote is
  found word for word in the source.
- **Optional Claude-assisted extraction.** Claude proposes extra events, and each proposal is
  accepted only if all four checks pass:
  1. its quote appears **verbatim** in the document;
  2. the time it gives is **actually stated** in that quote;
  3. its actor is a known person who is **named in the quote or is its speaker**;
  4. its location is a known place **named in the quote**.

  Rejected proposals are listed with the reason, so hallucinations are visible rather than silent.

### Try it

```bash
python -m detective timeline cases/case1_missing_laptop
python -m detective timeline cases/case1_missing_laptop --records
python -m detective timeline cases/case1_missing_laptop --person "Marcus Hale"
python -m detective search   cases/case1_missing_laptop "laptop drawer"
python -m detective entities cases/case1_missing_laptop

# Optional, needs the anthropic SDK and credentials:
pip install anthropic pydantic
export ANTHROPIC_API_KEY=...               # or: ant auth login
python -m detective timeline cases/case1_missing_laptop --llm
```

Example timeline rows:

```
2026-03-12 18:00        CLAIM   Marcus Hale @ Brightwave Office
                               "I left the office at 6 PM and went straight home."  [interview_marcus:L2]
2026-03-12 19:44        RECORD  Marcus Hale @ Design Lab
                               "2026-03-12 19:44 | Marcus Hale | Design Lab | ENTRY"  [badge_log:L7]
```

### Tests (22)

| File | What it checks |
|---|---|
| `test_loader.py` (3) | Case folder, front matter and answer key load correctly |
| `test_timeparse.py` (4) | Clock times, hedges, ranges, relative days |
| `test_entities.py` (3) | People and places found, aliases resolved to full names |
| `test_search.py` (2) | Relevant clues ranked first, person filter works |
| `test_timeline.py` (6) | Chronological order, records vs. claims, questions are not events, unidentified CCTV figure is not guessed |
| `test_grounding.py` (3) | Every quote is real; fabricated quotes are rejected |
| `test_llm_extract.py` (1) | Hallucinated LLM proposals are rejected with a reason (mocked, no API call) |

---

## Milestone 2: alibis, speculation and opportunity (~35%)

The system now checks what each person says about their whereabouts against the badge log and
CCTV, catches the lie, separates guesses from evidence, and shows who could have been at the
scene.

### What was built

- **Alibi checking.** Each first-person whereabouts claim is turned into a structured claim
  (departure, arrival, "didn't come back", present at a place, somewhere else). It is checked
  against a presence model built **only** from the badge log and CCTV. Every verdict quotes
  both the claim and the records behind it:
  - `SUPPORTED`: a record confirms it (Marcus's "left at 6 PM" vs. the 18:02 exit);
  - `CONSISTENT`: nothing conflicts, but the records can't confirm it (Priya's restaurant dinner);
  - `UNVERIFIED`: the records say nothing either way;
  - `CONTRADICTED`: a record rules it out (Marcus's "I didn't come back that night" vs. his
    19:41 entry and his 19:44 Design Lab badge).
- **Speculation flags.** Guesses ("it was probably Lena") and impressions ("Marcus has seemed
  stressed") are flagged with who said them and who they are about. They are never used as
  evidence.
- **Opportunity.** Each suspect is rated *at scene*, *on site* or *no recorded presence* for
  the crime window. Both ends of the window are quotes that must exist word for word in the
  evidence (an invented quote raises an error), and the times are read from those quotes.
- **Assumptions are stated.** Any conclusion that rests on missing records says so ("a missing
  record is not proof of absence").
- **Holdout case** (`tests/fixtures/holdout_violin`, "The Vanished Violin"): a second case with
  different people, places, wording and type of lie (a fake concert alibi rather than "didn't
  come back"). It matched its answer key on the first run, with no rule changes. It was written
  by the same author as the rules, so it is a check against overfitting, not proof of generality.

### Results on Case 1

| Suspect | Alibi | Opportunity |
|---|---|---|
| Marcus Hale | **Broken**: "didn't come back" vs. 19:41 entry and 19:44 Design Lab badge | At scene (19:44) |
| Priya Nair | Holds: left at 17:58; dinner consistent but unconfirmable | No recorded presence |
| Lena Torres | Holds: arrival, lab visit and exit all confirmed by badge log and CCTV | At scene (20:47) |
| Sam Whitfield | Holds: left at 18:40; video call from home consistent | On site until 18:40, never in the lab |

### Try it

```bash
python -m detective analyze     cases/case1_missing_laptop     # alibis + speculation + opportunity
python -m detective alibis      cases/case1_missing_laptop --person "Marcus Hale"
python -m detective speculation cases/case1_missing_laptop
python -m detective opportunity cases/case1_missing_laptop
python -m detective analyze     tests/fixtures/holdout_violin  # the holdout case
```

Example alibi check:

```
Marcus Hale (suspect): alibi BROKEN
  OK SUPPORTED    departure 18:00
       claim:  "I left the office at 6 PM and went straight home."  [interview_marcus:L2]
       record: "2026-03-12 18:02 | Marcus Hale | Main Entrance | EXIT"  [badge_log:L2]
  XX CONTRADICTED no_return 18:00-06:00
       claim:  "I didn't come back that night."  [interview_marcus:L2]
       record: "2026-03-12 19:41 | Marcus Hale | Main Entrance | ENTRY"  [badge_log:L6]
       record: "2026-03-12 19:44 | Marcus Hale | Design Lab | ENTRY"  [badge_log:L7]
```

### Tests (28)

| File | What it checks |
|---|---|
| `test_claims.py` (4) | Claims parsed with the right times and places; only the speaker's own first-person statements count |
| `test_alibi.py` (8) | Marcus's lie is caught with quotes from both sides; only the liar's alibi breaks; unconfirmable alibis stay "consistent"; a wrong time is caught |
| `test_speculation.py` (4) | Exactly the known guesses are flagged, and none is used as evidence |
| `test_opportunity.py` (6) | Window read from quoted evidence; access levels match the answer key; an invented window quote is rejected |
| `test_holdout.py` (5) | Same checks on the holdout case against its own answer key |
| `test_cli.py` (1) | `analyze` command reports the contradiction |

### Not yet covered

- Lies that movement records can't test, such as Marcus's "I've never talked to anyone there"
  vs. his recovered chat with a NovaForge recruiter. This belongs with motive analysis in
  milestone 3.
- Unidentified CCTV figures (the grey hoodie) are deliberately not matched to anyone.

---

## Architecture

```
cases/<case>/case.json        cast list, places (on/off site, entrances), scene, quoted window bounds
cases/<case>/documents/*.txt  evidence, each with front matter (id, type, date, author)
cases/<case>/solution.json    answer key: read only by tests, never by the pipeline
tests/fixtures/holdout_violin second case with its own answer key, used only by tests

detective/
  # Milestone 1
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
  # Milestone 2
  claims.py            first-person whereabouts claims (departure, arrival, no-return, present, elsewhere)
  presence.py          who was on site when, from badge log + CCTV only
  alibi.py             claim vs. records -> supported / consistent / unverified / contradicted
  speculation.py       guesses and impressions, flagged and kept out of the evidence
  opportunity.py       evidence-anchored crime window + at-scene / on-site / none per suspect
  # Shared
  pipeline.py          wires it together; final check that every quote it outputs is grounded
  cli.py               command-line explorer
```

## Design choices

- **Records vs. claims** is decided by document type, not by the LLM, so a confident witness
  can never be promoted to a fact.
- **Rules first, LLM second.** Rule-based extraction gives a deterministic, testable baseline;
  the LLM adds coverage on messy prose, behind the same grounding checks.
- **Claims are checked against records, never the reverse.** The presence model is built from
  movement logs only, so a witness can't place themselves (or anyone else) at the scene.
- **Two levels of "fine".** `SUPPORTED` needs a confirming record; `CONSISTENT` only means
  nothing conflicts. An alibi nobody can check is never reported as confirmed.
- **The model never sees the answer key.** `solution.json` is used only for evaluation.
