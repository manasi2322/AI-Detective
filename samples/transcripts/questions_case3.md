# Follow-up questions: The Leaked Formula

Generated with `python -m detective ask cases/case3_leaked_formula "<question>"`.

## Who did it?

```
Most likely: Noah Fisk (+4.0), confidence medium.
- Noah Fisk leads Iris Kemp by 4.5 points.
- Record-backed facts add +0.5, statements add +5.5 and assumptions add +1.0 to Noah Fisk's score.
- If every assumption were wrong, the lead would be 3.5 points.
- +2.0 claim: Denied contact with Rhea Vance, but recovered messages show it.
- +1.5 claim: Motive: gain (reported by Rhea Vance): "pay you"
- +1.0 claim: Motive: money (said it themselves): "money"

Evidence:
  [statement] “I've never spoken to anyone at Veltrix.” [interview_noah:L6]
  [statement] “[2026-10-05 19:20] Rhea Vance: Veltrix will pay you 50,000 for the formula. Bring it on a USB stick.” [chat_noah_rhea:L1]
  [statement] “[2026-10-05 19:31] Noah Fisk: I need the money to clear my debts. Wednesday night, when the lab is quiet.” [chat_noah_rhea:L2]
```

## Where was Iris at 22:15?

```
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
```

## Did Noah lie?

```
Yes. 1 statement by Noah Fisk is contradicted by the evidence:
- “I've never spoken to anyone at Veltrix.” [interview_noah:L6]: recovered messages show contact with Rhea Vance.
A contradiction shows a statement is false; it does not by itself show why they lied.

Evidence:
  [statement] “I've never spoken to anyone at Veltrix.” [interview_noah:L6]
  [statement] “[2026-10-05 19:20] Rhea Vance: Veltrix will pay you 50,000 for the formula. Bring it on a USB stick.” [chat_noah_rhea:L1]
  [statement] “[2026-10-05 19:31] Noah Fisk: I need the money to clear my debts. Wednesday night, when the lab is quiet.” [chat_noah_rhea:L2]
```

## Is Noah's alibi solid?

```
Noah Fisk's alibi holds: nothing in the records contradicts it:
- SUPPORTED: “I came back at 9:40 PM to restart the centrifuge.” [interview_noah:L2]. Records show Noah Fisk entering at 21:40 [badge_log:L3]; claimed 21:40.
- SUPPORTED: “I was in the Lab Wing from 10:05 PM to 10:40 PM.” [interview_noah:L2]. Records put Noah Fisk at Lab Wing at 22:09 [badge_log:L4]; claimed 22:05.
- SUPPORTED: “I left at 10:45 PM.” [interview_noah:L2]. Records show Noah Fisk leaving at 22:47 [badge_log:L6]; claimed 22:45.

Evidence:
  [statement] “I came back at 9:40 PM to restart the centrifuge.” [interview_noah:L2]
  [record] “2026-10-07 21:40 | Noah Fisk | Main Door | ENTRY” [badge_log:L3]
  [statement] “I was in the Lab Wing from 10:05 PM to 10:40 PM.” [interview_noah:L2]
  [record] “2026-10-07 22:09 | Noah Fisk | Lab Wing | ENTRY” [badge_log:L4]
  [statement] “I left at 10:45 PM.” [interview_noah:L2]
  [record] “2026-10-07 22:47 | Noah Fisk | Main Door | EXIT” [badge_log:L6]
```

## Who had the opportunity?

```
Crime window: 10-07 17:00 -> 10-08 09:30 at Lab Wing.
- Iris Kemp: on site. On the premises during the window (? -> 10-07 22:18; 10-07 22:19 -> 10-07 22:19), but no record puts Iris Kemp at Lab Wing.
- Noah Fisk: at scene. Records put Noah Fisk at Lab Wing at 22:09 [badge_log:L4], inside the window.
- Paul Ortega: on site. On the premises during the window (? -> 10-07 18:30), but no record puts Paul Ortega at Lab Wing.
- Zara Quinn: on site. On the premises during the window (? -> 10-07 19:05), but no record puts Zara Quinn at Lab Wing.

Evidence:
  [record] “2026-10-07 22:18 | Iris Kemp | Main Door | EXIT” [badge_log:L5]
  [record] “2026-10-07 22:19 | Car Park camera | Iris Kemp walks to her car and drives away.” [cctv:L2]
  [record] “2026-10-07 22:09 | Noah Fisk | Lab Wing | ENTRY” [badge_log:L4]
  [record] “2026-10-07 18:30 | Paul Ortega | Main Door | EXIT” [badge_log:L1]
  [record] “2026-10-07 19:05 | Zara Quinn | Main Door | EXIT” [badge_log:L2]
```
