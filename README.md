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
| 3 | Disputed records, motives, links, investigator with a labelled reasoning log | Done (~60%) | 17 |
| 4 | Cases 2 and 3 (twisted / impossible), follow-up questions, new-evidence reassessment | Next | |
| 5 | Final case reports, evaluation harness across all cases | Planned | |

**Total: 67 automated tests, all passing.**

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pytest
pytest -q                                   # 67 passed
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

### Left for milestone 3 (now done)

- Lies that movement records can't test, such as Marcus's "I've never talked to anyone there"
  vs. his recovered chat with a NovaForge recruiter.
- Unidentified CCTV figures (the grey hoodie). Milestone 2 doesn't match them to anyone;
  milestone 3 does, labelled as an assumption.

---

## Milestone 3: motives, links and the investigator (~60%)

The system now weighs everything it has found. For each suspect it builds one reasoning log
in which every step is labelled, weighted and backed by exact quotes, then names the most likely
suspect with a confidence level.

### What was built

- **Disputed records** (`records.py`). A badge or login proves the card was used, not who used
  it. If CCTV shows the same person somewhere else within 5 minutes of a badge swipe, the swipe
  is marked as disputed and left out of the alibi and opportunity checks.
- **Motives** (`motive.py`). Statements that give someone a reason to act: **gain** (an offer
  or reward for the item), **intent** (a stated plan to take it), **money** trouble, **conflict**
  (an argument or refusal) and **need** (the person says they want the item). Each motive records
  who it belongs to and whether they said it themselves or someone else reported it. Guesses
  ("seemed stressed about money") are never treated as motives.
- **Links** (`links.py`).
  - *CCTV matches:* an unnamed person on camera is matched to someone only if exactly one person
    has a record within 5 minutes. A match is always labelled an **assumption**. A later line
    that refers back ("the same grey-hoodie figure") inherits the match.
  - *Hidden connections:* a suspect and an outside party who appear in the same chat or email
    are connected. If the suspect denied contact in an interview, the denial is shown next to
    the messages that contradict it.
- **Investigator** (`investigator.py`). One reasoning log per suspect. Every step has:
  - a **label**:
    - `FACT`: decided by records (badge log, login log, CCTV, brief);
    - `CLAIM`: rests on what someone said or wrote;
    - `ASSUMPTION`: an inference, such as a CCTV match or "no record means absent";
    - `SPECULATION`: a guess, which always weighs 0;
  - a **weight**, where positive points toward the suspect and negative away;
  - **exact quotes** from the documents.

  Scores are the sum of the weights. All weights are in one table (`WEIGHTS`) so the scoring
  policy is easy to review. A confidence level (high / medium / low) comes from the lead over the
  runner-up and from whether a record-backed fact points to the top suspect.
- **Optional LLM investigator.** Claude proposes extra steps, which pass through the same
  `validate` rules as the rules engine: quotes must be found word for word, a `FACT` may only
  cite records, `SPECULATION` must weigh 0 and weights stay within ±3. Anything else is rejected
  with the reason.

### Results on Case 1

| Suspect | Score | Main reasons |
|---|---|---|
| **Marcus Hale** | **+11.5** | Alibi contradicted by badge log (+3); at the scene and never said so (+2); job offer conditional on the prototype (+1.5); grey-hoodie CCTV figure matched by timing (+1, +1, assumptions); chat with NovaForge recruiter (+1) that he denied (+2) |
| Sam Whitfield | −0.5 | Alibi confirmed (−1) and consistent (−0.5); asked to borrow the laptop and was refused (+0.5 need, +0.5 conflict) |
| Lena Torres | −2.5 | Arrival, lab visit and exit all confirmed (−3); at the scene but said so and records agree (+0.5) |
| Priya Nair | −3.0 | Left before the window (−1); dinner consistent (−0.5); no recorded presence (−1.5, assumption) |

Most likely: **Marcus Hale**, confidence **high** (12-point lead, backed by record facts).
On the holdout case Tomas Reyes scores +12.5 and the other three are negative.

Sam does get a motive: he asked to borrow the laptop and was refused. That is real evidence
(the answer key lists it as a red-herring motive), so the system reports it rather than hiding
it, and the alibi and opportunity evidence outweigh it.

### Try it

```bash
python -m detective investigate cases/case1_missing_laptop                       # full reasoning log + conclusion
python -m detective investigate cases/case1_missing_laptop --person "Marcus Hale"
python -m detective motives     cases/case1_missing_laptop
python -m detective links       cases/case1_missing_laptop                       # CCTV matches, connections, disputes
python -m detective links       tests/fixtures/disputed_badge                    # a badge disputed by CCTV
python -m detective investigate cases/case1_missing_laptop --llm                 # add Claude's steps (needs credentials)
```

Example reasoning steps:

```
Marcus Hale: score +11.5
  +3.0  FACT        alibi: Alibi contradicted: Claims to be off the premises from 18:00 to 03-13 06:00, but records put them at Main Entrance at 19:41 [badge_log:L6], at Design Lab at 19:44 [badge_log:L7].
          tested: "I didn't come back that night."  [interview_marcus:L2]
          cites:  "2026-03-12 19:41 | Marcus Hale | Main Entrance | ENTRY"  [badge_log:L6]
  +1.0  ASSUMPTION  link: Unnamed person on CCTV matched by timing: Only Marcus Hale has a record within 5 min of this sighting (badge_log:L6, badge_log:L7). Assumed, not identified: the face is not described.
  +0.0  SPECULATION speculation: Priya Nair impression: "seemed". Not evidence; weighs nothing.

== CONCLUSION ==
  ranking: Marcus Hale +11.5, Sam Whitfield -0.5, Lena Torres -2.5, Priya Nair -3.0
  most likely: Marcus Hale  (confidence: high; Marcus Hale leads by 12.0 points; at least one record-backed fact points to them.)
```

### Tests (17)

| File | What it checks |
|---|---|
| `test_records.py` (2) | Case 1 has no disputed records; a badge disputed by CCTV is left out of alibi and opportunity |
| `test_motive.py` (4) | Motive types match both answer keys; the culprit's motive is cited and reported by someone else; guesses are never motives; the culprit has the strongest motive |
| `test_links.py` (3) | CCTV matches are labelled assumptions and match both answer keys; they cite the records they rely on; hidden connections and denials are found |
| `test_investigator.py` (7) | Every step is labelled, cited and grounded; facts cite only records; speculation never changes a score; the evidence favours the culprit in both cases (lead of 5+ points, everyone else negative); a fact citing a statement is rejected; LLM steps follow the same rules |
| `test_cli.py` (+1) | `investigate`, `motives` and `links` commands |

New fixtures: `tests/fixtures/disputed_badge` (Nora's badge opens the Server Room while CCTV
shows her in the canteen), plus a recovered chat with a buyer and a denial added to the holdout.

### Not yet covered

- The weights are a hand-set policy, not learned. They are tested on two cases, both written by
  the same author as the rules, so Cases 2 and 3 will be the real test.
- The LLM investigator is only tested offline with a fake. It has not been run against Claude
  in this repo's tests.

---

## Architecture

```
cases/<case>/case.json        cast list (suspects, outside parties), places (on/off site, entrances), scene, item, quoted window bounds
cases/<case>/documents/*.txt  evidence, each with front matter (id, type, date, author)
cases/<case>/solution.json    answer key: read only by tests, never by the pipeline
tests/fixtures/holdout_violin second case with its own answer key, used only by tests
tests/fixtures/disputed_badge small case where CCTV disputes a badge swipe

detective/
  # Milestone 1
  loader.py            parse case folder + front matter
  segments.py          split documents into citable sentences / log lines, track speakers
  grounding.py         Quote creation + verification (the anti-hallucination layer)
  timeparse.py         clock times, hedges, ranges, relative days
  entities.py          roster/alias matching for people and places
  events.py            rule-based timed-event extraction
  llm_extract.py       LLM proposals -> validated Events or Rejections
  anthropic_backend.py Claude calls with structured output: event extraction, investigator steps (lazy import)
  store.py             BM25 evidence search
  timeline.py          ordering, record/claim split, per-person views, rendering
  # Milestone 2
  claims.py            first-person whereabouts claims (departure, arrival, no-return, present, elsewhere)
  presence.py          who was on site when, from badge log + CCTV only
  alibi.py             claim vs. records -> supported / consistent / unverified / contradicted
  speculation.py       guesses and impressions, flagged and kept out of the evidence
  opportunity.py       evidence-anchored crime window + at-scene / on-site / none per suspect
  # Milestone 3
  records.py           badge/login records disputed by CCTV, kept out of presence
  motive.py            gain / intent / money / conflict / need, with owner and who reported it
  links.py             CCTV matches by timing (assumptions), hidden connections + denials
  investigator.py      labelled, weighted, cited reasoning log; scores; confidence; LLM step validation
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
- **A badge is not a person.** Card and login records can be disputed by CCTV; a camera can't
  be disputed by a card.
- **One set of rules for rules and LLM.** Every reasoning step, whoever wrote it, goes through
  the same `validate` check before it can change a score.
- **Speculation is shown, never counted.** Guesses appear in the log so the investigator can
  see them, with weight 0.
- **The model never sees the answer key.** `solution.json` is used only for evaluation.
