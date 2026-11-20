# Chat session: The Leaked Formula, starting from the first evidence stage

Generated with `python -m detective chat cases/case3_leaked_formula --stage 1`. Lines starting with `detective>` are what the investigator typed.

```
Investigating: The Leaked Formula (impossible), 8 documents, evidence stage 1 of 2. Type :help for commands.

Most likely: Iris Kemp (confidence medium)
  Iris Kemp            +1.5
  Paul Ortega          -1.0
  Zara Quinn           -1.0
  Noah Fisk            -2.5
  Iris Kemp leads Paul Ortega by 2.5 points. Record-backed facts add +2.0, statements add +0.5 and assumptions add +0.0 to Iris Kemp's score. If every assumption were wrong, the lead would be 2.5 points.

detective> Who did it?
Most likely: Iris Kemp (+1.5), confidence medium.
- Iris Kemp leads Paul Ortega by 2.5 points.
- Record-backed facts add +2.0, statements add +0.5 and assumptions add +0.0 to Iris Kemp's score.
- If every assumption were wrong, the lead would be 2.5 points.
- +2.0 fact: Records put Iris Kemp at Lab Wing at 22:15 [login_log:L1], inside the window. They never mentioned it.
- +0.5 claim: Motive: conflict (reported by Paul Ortega): "furious"

Evidence:
  [record] “2026-10-07 22:15 | Iris Kemp | Lab Terminal 3 | LOGIN, downloaded formula_v7.pdf” [login_log:L1]
  [statement] “Iris was furious about being passed over for the lab director job last month.” [interview_paul:L4]


detective> Did Iris lie?
No. None of Iris Kemp's 1 checkable statements is contradicted by records.
- Confirmed: “I worked late in my office and left at about 10:15 PM.” [interview_iris:L2]: Records show Iris Kemp leaving at 22:18 [badge_log:L5]; claimed ~22:15.

Evidence:
  [statement] “I worked late in my office and left at about 10:15 PM.” [interview_iris:L2]
  [record] “2026-10-07 22:18 | Iris Kemp | Main Door | EXIT” [badge_log:L5]


detective> :uncover
New evidence (2 documents):
  + cctv (cctv): CCTV review (requested on day 2)
  + chat_noah_rhea (chat): Messages recovered from Noah Fisk's phone (day 2)

The conclusion CHANGED: Iris Kemp (medium) -> Noah Fisk (medium).

  Suspect              before   after   change
  Noah Fisk              -2.5    +4.0    +6.5
  Iris Kemp              +1.5    -0.5    -2.0
  Paul Ortega            -1.0    -1.0    +0.0
  Zara Quinn             -1.0    -1.0    +0.0

  Iris Kemp:
    - no longer counted (+2.0): Records put Iris Kemp at Lab Wing at 22:15 [login_log:L1], inside the window. They never mentioned it.

  Noah Fisk:
    + new (+1.5): Motive: gain (reported by Rhea Vance): "pay you"
    + new (+1.0): Motive: money (said it themselves): "money"
    + new (+1.0): Unnamed person on CCTV matched by timing: Only Noah Fisk has a record within 5 min of this sighting (badge_log:L4). Assumed, not identified: the face is not described.
    + new (+1.0): Hidden connection: Noah Fisk and outside party Rhea Vance exchange messages in chat_noah_rhea. Noah Fisk denied any such contact [interview_noah:L6].
    + new (+2.0): Denied contact with Rhea Vance, but recovered messages show it.

  Newly disputed record: Iris Kemp's credential was used at Lab Wing at 22:15 [login_log:L1], but CCTV shows Iris Kemp at Car Park 4 min away in time [cctv:L2]. The card was used; who used it is in doubt.

  New contradiction: Noah Fisk and outside party Rhea Vance exchange messages in chat_noah_rhea. Noah Fisk denied any such contact [interview_noah:L6].


detective> Did Noah lie?
Yes. 1 statement by Noah Fisk is contradicted by the evidence:
- “I've never spoken to anyone at Veltrix.” [interview_noah:L6]: recovered messages show contact with Rhea Vance.
A contradiction shows a statement is false; it does not by itself show why they lied.

Evidence:
  [statement] “I've never spoken to anyone at Veltrix.” [interview_noah:L6]
  [statement] “[2026-10-05 19:20] Rhea Vance: Veltrix will pay you 50,000 for the formula. Bring it on a USB stick.” [chat_noah_rhea:L1]
  [statement] “[2026-10-05 19:31] Noah Fisk: I need the money to clear my debts. Wednesday night, when the lab is quiet.” [chat_noah_rhea:L2]


detective> Where was Iris at 22:15?
At 22:15 on 10-07, the records put Iris Kemp on the premises.
- Record 22:18: Main Door [badge_log:L5]
- Record 22:19: Car Park [cctv:L2]
- Set aside: a record at 22:15 is disputed and not used. Iris Kemp's credential was used at Lab Wing at 22:15 [login_log:L1], but CCTV shows Iris Kemp at Car Park 4 min away in time [cctv:L2]. The card was used; who used it is in doubt.
- Iris Kemp said: “I worked late in my office and left at about 10:15 PM.” [interview_iris:L2], which is supported by the records.

Evidence:
  [record] “2026-10-07 22:18 | Iris Kemp | Main Door | EXIT” [badge_log:L5]
  [record] “2026-10-07 22:19 | Car Park camera | Iris Kemp walks to her car and drives away.” [cctv:L2]
  [record] “2026-10-07 22:15 | Iris Kemp | Lab Terminal 3 | LOGIN, downloaded formula_v7.pdf” [login_log:L1]
  [statement] “I worked late in my office and left at about 10:15 PM.” [interview_iris:L2]


detective> :who
Most likely: Noah Fisk (confidence medium)
  Noah Fisk            +4.0
  Iris Kemp            -0.5
  Paul Ortega          -1.0
  Zara Quinn           -1.0
  Noah Fisk leads Iris Kemp by 4.5 points. Record-backed facts add +0.5, statements add +5.5 and assumptions add +1.0 to Noah Fisk's score. If every assumption were wrong, the lead would be 3.5 points.


detective> :quit
```
