# AI Detective: design and technical explanation

## 1. The problem and the approach

The task is to name the most likely culprit from a case file full of witness interviews, chats,
emails, CCTV summaries and access logs, where some evidence is misleading, some witnesses lie and
some clues are irrelevant. The brief asks for more than "ask an LLM who did it": the system has to
show how it reasoned and what each conclusion rests on.

The design follows from that:

1. **Evidence is data with a source.** Every piece of evidence the system uses is a `Quote`:
   document id, character span, line number and the exact text. Nothing without a quote can enter
   the reasoning.
2. **Records and statements are kept apart.** A badge log or CCTV summary is a *record*; an
   interview, chat or email is a *statement*, which may be a lie. The split comes from the
   document type, never from a model's opinion.
3. **Rules do the reasoning; the LLM is checked by the same rules.** Deterministic, rule-based
   analysis gives a baseline that can be tested exactly. Claude can add events, reasoning steps
   and answers, but each of those goes through the same validation as the rules engine and is
   rejected, with a reason, if it cites anything that isn't in the documents.
4. **Every conclusion is a sum of labelled, cited steps.** The verdict is the suspect with the
   highest total. Each step is labelled fact, claim, assumption or speculation, so a reader can
   see how much of the case rests on records and how much on inference.

## 2. Pipeline

```
case folder ──► loader ──► segments ──► entities ──► events ──► timeline
 (case.json,                (sentences,   (people,     (timed,     (records vs
  documents/*.txt,           log lines,    places,      grounded)   statements)
  solution.json*)            speakers)     aliases)         │
                                                             ▼
                      ┌──────────── presence model (records only) ◄── disputed records removed
                      │                    │
 claims (first-person, vouches, sightings) ─┤──► alibi checks ──► statement conflicts
                      │                    │
                      │                    └──► opportunity (crime window from quoted evidence)
 motives ─────────────┤
 links (CCTV matches, hidden connections) ─┤
 speculation (flagged) ────────────────────┤
                                           ▼
                                  investigator: labelled, weighted, cited steps per suspect
                                           │
             ┌──────────────┬──────────────┼───────────────┬───────────────┐
             ▼              ▼              ▼               ▼               ▼
          report         questions     reassessment     web UI / chat   evaluation
      (citations       (answers with   (re-run on new                  (vs solution.json)
        checked)        checked quotes)  evidence, diff)

* solution.json is read only by the evaluation and the tests, never by the pipeline.
```

Every arrow is a pure function of the case files, so the whole investigation is re-run from
scratch whenever evidence changes. Nothing is cached between runs.

## 3. Evidence model

| Concept | Where | Notes |
|---|---|---|
| `Document` | `models.py`, `loader.py` | Front matter: `id`, `type`, `title`, `date`, optional `author`, optional `stage` (evidence uncovered later) |
| Record types | `badge_log`, `login_log`, `cctv`, `brief` | Card and login records (`CREDENTIAL_TYPES`) show a card or account was used, not who used it |
| Statement types | `interview`, `chat`, `email`, `notice` | May be lies; always labelled as statements |
| `Quote` | `models.py`, `grounding.py` | `body[start:end] == text`; `verify()` re-checks it against the document |
| `Event` | `events.py`, `llm_extract.py` | A time (or range), actor, place, people and the quote it came from |
| Locations | `case.json` | `onsite` / `entrance` flags drive the presence model; the case also declares the `scene`, the stolen `item` and the crime `window` (as quotes) |

## 4. Extraction and retrieval

- **Segmentation** (`segments.py`) splits documents into citable units: log lines for records and
  chats, sentences for prose. Interview questions are kept apart from answers, because a question
  is not evidence.
- **Entities** (`entities.py`) match the case roster with aliases ("Marcus" → Marcus Hale, "the
  lab" → Design Lab). The longest alias wins, so "Marcus Hale" is one mention, not two.
- **Times** (`timeparse.py`) cover `2026-03-12 19:44`, `6 PM`, `6:15 PM`, `19:44`, `midnight`,
  hedges ("about", "a bit before" → approximate), ranges ("from 7 PM until about 9:30 PM") and
  relative days ("the next morning", "on Friday").
- **LLM extraction** (`llm_extract.py`, optional) asks Claude for more events. A proposal is kept
  only if all four checks pass:
  1. the quote is verbatim in the document;
  2. the time is stated in that quote;
  3. the actor is a known person named in the quote, or its speaker;
  4. the place is named in the quote.
- **Retrieval** (`store.py`) is BM25 over the segments, with person and document-type filters.
  BM25 is deterministic and needs no model, so retrieval can be tested exactly, and every hit is
  already a citable quote. With cases of 10–15 documents, keyword ranking finds the key clue in
  the top 5 for every key fact in the answer keys (retrieval@5 = 100%).

## 5. Reasoning

**Presence** (`presence.py`) is built from movement records only (badge, login, CCTV) and never
from statements. Entries and exits through doors marked `entrance` become stays on the premises.
A sighting with no direction, such as a phone joining the Wi-Fi at a door, counts as being on site
at that moment. Unnamed people on CCTV are never assigned to anyone here.

**Disputed records** (`records.py`): if a card or login record puts someone in one place and CCTV
shows that person somewhere else within 5 minutes, the card record is disputed and removed from
the presence model. A camera shows a person; a reader only shows a card. Door records aren't
disputed by sightings that fit their direction: badging out at 22:18 and being on the car park
camera at 22:19 is one trip, not a conflict.

**Claims** (`claims.py`) are first-person whereabouts statements:
- departure ("I left at 6 PM");
- arrival ("my shift began at 10 PM");
- no return ("I didn't come back that night");
- present at a place ("I cleaned the Design Lab at around 8:45 PM");
- elsewhere ("dinner at Lantern Bistro from 7 PM").

They also cover statements about other people: a **vouch** ("Victor was with me at my flat") and a
**sighting** ("I saw Victor near the side door"). These keep `reported_by`, so a friend's word is
never mistaken for the person's own account, or for a record.

**Alibi checks** (`alibi.py`) give each claim one verdict against the presence model:

| Verdict | Meaning | Example |
|---|---|---|
| `SUPPORTED` | A record confirms it | "left at 6 PM" vs a badge exit at 18:02 |
| `CONSISTENT` | Nothing conflicts, but no record can confirm it | a restaurant dinner |
| `UNVERIFIED` | No records either way | |
| `CONTRADICTED` | A record rules it out | "didn't come back" vs a badge entry at 19:41 |

The tolerance is 10 minutes, or 15 for hedged times. `CONSISTENT` is never reported as confirmed.

**Statement conflicts** (`statements.py`): two people placing the same person in different places
at overlapping times, one of them off the premises. Where only one side is contradicted by
records, the conflict is resolved in favour of the other side.

**Opportunity** (`opportunity.py`): the crime window's two ends are quotes in `case.json` that
must exist word for word, and the times are read from those quotes. An invented window quote
raises an error. Each suspect is then rated *at scene*, *on site* or *no recorded presence*.

**Motives** (`motive.py`): gain, intent, money, conflict and need, each with its owner and whether
the person said it themselves or someone else reported it. Guesses ("seemed stressed about money")
are flagged by `speculation.py` and never become motives.

**Links** (`links.py`):
- An unnamed CCTV figure is matched to someone only if exactly one person has a record within
  5 minutes. A match is always an assumption, and a later "the same man" line inherits it.
- A suspect who exchanged messages with an outside party is connected to them. If the suspect also
  denied contact in an interview, the denial is reported next to the messages.

## 6. The investigator and confidence

`investigator.py` turns every finding into steps for each suspect:

| Label | Means | Rule |
|---|---|---|
| FACT | decided by records | every quote must come from a record document |
| CLAIM | rests on what someone said or wrote | |
| ASSUMPTION | an inference (CCTV match by timing, "no record means absent") | |
| SPECULATION | a guess | weight must be 0 |

Weights live in one table (`WEIGHTS`), so the scoring policy is easy to review. Positive points
toward the suspect, negative away:

| Step | Weight | Step | Weight |
|---|---|---|---|
| Own alibi contradicted | +3.0 | At the scene, never mentioned it | +2.0 |
| Denied contact, messages show it | +2.0 | Intent to take the item | +2.0 |
| Offer or reward for the item | +1.5 | Money trouble | +1.0 |
| CCTV figure matched by timing | +1.0 | Hidden connection | +1.0 |
| Friend's alibi for them is false | +1.0 | Witness sighting confirmed by records | +1.0 |
| Witness sighting, unconfirmed | +0.5 | At the scene, disclosed and confirmed | +0.5 |
| Conflict / need | +0.5 | On site, not at the scene | 0 |
| Alibi part confirmed by a record | −1.0 | Alibi part consistent only | −0.5 |
| Friend's alibi confirmed | −0.5 | No recorded presence in the window | −1.5 |

Two rules stop true details from excusing a liar:
- If any part of a suspect's own account is contradicted, the true parts of that account weigh 0.
- A friend's unconfirmed alibi weighs 0.

**Confidence** (`Assessment.confidence_reasons`):
- **high:** the lead over the runner-up is at least 5 points, at least one record-backed fact
  points to the leader, and the lead would still be at least 3 if every assumption were wrong;
- **medium:** a lead of 2 or more, backed by a fact (or a lead of at least 3);
- **low:** anything else.

The explanation always states the lead, how much of the leader's score comes from facts,
statements and assumptions, and the lead without assumptions. Case 3 ends at **medium**: Noah's
own account is true, and the case against him rests on statements (a chat and a denial) more than
on records.

## 7. Preventing invented evidence

Several layers, each tested:

1. **Extraction:** rule-based items are built from document spans, so they can't be invented. LLM
   proposals must pass the four checks in section 4.
2. **Pipeline guard:** `investigate()` re-verifies every quote it outputs (events, claims, alibi
   evidence, motives, links, steps) and raises if any fails.
3. **Investigator steps:** `validate()` applies the same rules to rule-based and LLM steps: real
   quotes only, facts only from records, speculation at 0, weights within ±3.
4. **Follow-up answers:** LLM answers keep only the quotes found in the documents and list the
   dropped ones. With no valid quotes, the rules answer is shown instead.
5. **Reports:** `check_citations()` parses the *finished Markdown*, not the objects used to build
   it, so a bug in the report code can't produce a citation that doesn't exist. Every “quote”
   [doc:Lnn] must appear on that line; every [doc:Lnn] reference must exist. A report with a bad
   citation is refused.
6. **Grounding attack** (in the evaluation): for each case, about 30 believable fakes go through
   the event extractor, the investigator and the answerer. A fake is the real line with one detail
   changed (19:41 → 19:44), or a fact citing a statement, or weighted speculation. All of them are
   rejected, and all genuine counterparts are accepted.

## 8. Resisting misleading evidence (by case)

| Trap | Case | How it is handled |
|---|---|---|
| Speculative accusation ("it was probably Lena") | 1, 2, 3 | Flagged as speculation, weight 0 |
| Red-herring motive (Sam wanted the laptop for a demo) | 1 | Reported, but outweighed by his confirmed departure and no scene access |
| Irrelevant documents (kitchen notice, parking memo) | 1, 2, 3 | No timed claims or motives come from them; they never enter a verdict |
| "Perfect" alibi from a friend | 2 | Kept as Celia's statement about Victor; the Wi-Fi log contradicts it |
| Guard's badge used by someone else | 2 | CCTV disputes the swipe; it is removed from presence and opportunity |
| Witnesses contradict each other | 2 | Conflict found and resolved by records in favour of the cleaner |
| Evidence first points to the wrong person | 3 | Stage 1 names Iris; stage 2 disputes her login, matches the CCTV figure to Noah and exposes his denial |
| Culprit whose own timeline is true | 3 | Alibi holds, but the denial, motive and CCTV match outweigh it; confidence stays medium |

## 9. Follow-up questions, reassessment and interfaces

- **Questions** (`qa.py`) are answered from the structured findings, not from free text:
  lie, where, who was at a place, motive, alibi, why / why not, culprit, confidence,
  contradictions, opportunity, connections, what happened at a time. Anything else falls back to
  evidence search, with no conclusion drawn. Each citation is tagged record, statement, assumption
  or speculation. Unknown names are said to be unknown, not guessed.
- **Reassessment** (`reassess.py`): uncovering a stage or adding a document re-runs everything and
  compares the before/after rankings, confidence, the steps that stopped counting or were added for
  each suspect, new disputes and new contradictions.
- **Interfaces:** the CLI (`python -m detective <command>`), an interactive chat (`chat`), and a
  local web UI (`web`). The web UI uses only the standard library, keeps no server state, accepts
  only known case folders, and caps request size.

## 10. Evaluation

`python evaluate.py` runs every case and turns each item in its answer key into a pass/fail check:

- the culprit;
- confidence not low;
- the early wrong lead (Case 3);
- each lie caught;
- honest alibis intact;
- red herrings below the culprit;
- disputed records;
- statement conflicts;
- speculation;
- motives;
- CCTV matches;
- connections;
- opportunity;
- key timeline events;
- retrieval@5;
- the grounding attack;
- report citations.

| Case | Named | Confidence | Timeline | Retrieval@5 | Invented rejected | Checks |
|---|---|---|---|---|---|---|
| The Missing Prototype Laptop (easy) | Marcus Hale ✓ | high | 100% | 100% | 100% | 35/35 |
| The Gallery Switch (twisted) | Victor Lane ✓ | high | 100% | 100% | 100% | 37/37 |
| The Leaked Formula (impossible) | Noah Fisk ✓ | medium | 100% | 100% | 100% | 37/37 |

There are 131 automated tests (`pytest -q`), including a holdout case and a disputed-badge fixture.

## 11. Limits

- **The cases and the rules have the same author.** Each case needed some general engine changes
  (witness vouches, door-aware disputes, midnight), but no case-specific rules or weights. A case
  written by someone else would be a stronger test, and the 100% scores should be read with that
  in mind.
- **The rules cover the phrasing patterns in these cases.** Unusual phrasing ("I popped out for a
  bit around nine") may be missed. The LLM extractor exists for that, behind the same checks.
- **The weights are a hand-set policy, not learned.** They are in one table for that reason.
- **The live LLM run has not been done yet.** The machine had no API credentials. The LLM paths are
  verified offline with stand-in models and the grounding attack. `python -m detective llm-run`
  records a real run in `samples/llm_runs/`.
- **Absence of a record is treated as an assumption, never as a fact,** and is labelled that way.

## 12. Adding a case

1. Create `cases/<id>/case.json` with:
   - the people (`suspect`, `outside`, aliases) and locations (`onsite`, `entrance`, aliases);
   - the `scene` and the stolen `item`;
   - the crime `window`, as two quotes from the documents.
2. Add `cases/<id>/documents/*.txt`, each with front matter. Use `stage: 2` for evidence uncovered
   later.
3. Add `cases/<id>/solution.json` with the culprit and any of the checkable keys used by the
   existing cases.
4. Run `python evaluate.py -v` and `python -m detective report cases/<id>`.
