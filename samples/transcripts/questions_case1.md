# Follow-up questions: The Missing Prototype Laptop

Generated with `python -m detective ask cases/case1_missing_laptop "<question>"`.

## Who did it?

```
Most likely: Marcus Hale (+11.5), confidence high.
- Marcus Hale leads Sam Whitfield by 12.0 points.
- Record-backed facts add +5.0, statements add +4.5 and assumptions add +2.0 to Marcus Hale's score.
- If every assumption were wrong, the lead would be 10.0 points.
- +3.0 fact: Alibi contradicted: Claims to be off the premises from 18:00 to 03-13 06:00, but records put them at Main Entrance at 19:41 [badge_log:L6], at Design Lab at 19:44 [badge_log:L7].
- +2.0 fact: Records put Marcus Hale at Design Lab at 19:44 [badge_log:L7], inside the window. They never mentioned it.
- +2.0 claim: Denied contact with Alex Brandt, but recovered messages show it.

Evidence:
  [record] “2026-03-12 19:41 | Marcus Hale | Main Entrance | ENTRY” [badge_log:L6]
  [record] “2026-03-12 19:44 | Marcus Hale | Design Lab | ENTRY” [badge_log:L7]
  [statement] “I've never talked to anyone there.” [interview_marcus:L6]
  [statement] “[2026-03-10 21:14] Alex Brandt: NovaForge can make you an offer, but the team wants to see the Brightwave prototype first.” [chat_marcus_alex:L1]
  [statement] “[2026-03-10 21:16] Marcus Hale: The prototype is on Daniel's laptop. He keeps it locked in the lab.” [chat_marcus_alex:L2]
```

## Did Marcus lie?

```
Yes. 2 statements by Marcus Hale are contradicted by the evidence:
- “I didn't come back that night.” [interview_marcus:L2]: Claims to be off the premises from 18:00 to 03-13 06:00, but records put them at Main Entrance at 19:41 [badge_log:L6], at Design Lab at 19:44 [badge_log:L7].
- “I've never talked to anyone there.” [interview_marcus:L6]: recovered messages show contact with Alex Brandt.
A contradiction shows a statement is false; it does not by itself show why they lied.

Evidence:
  [statement] “I didn't come back that night.” [interview_marcus:L2]
  [record] “2026-03-12 19:41 | Marcus Hale | Main Entrance | ENTRY” [badge_log:L6]
  [record] “2026-03-12 19:44 | Marcus Hale | Design Lab | ENTRY” [badge_log:L7]
  [statement] “I've never talked to anyone there.” [interview_marcus:L6]
  [statement] “[2026-03-10 21:14] Alex Brandt: NovaForge can make you an offer, but the team wants to see the Brightwave prototype first.” [chat_marcus_alex:L1]
  [statement] “[2026-03-10 21:16] Marcus Hale: The prototype is on Daniel's laptop. He keeps it locked in the lab.” [chat_marcus_alex:L2]
```

## Did Sam lie?

```
No. None of Sam Whitfield's 2 checkable statements is contradicted by records.
- Confirmed: “I left at 6:40 PM.” [interview_sam:L2]: Records show Sam Whitfield leaving at 18:40 [badge_log:L5]; claimed 18:40.
- Not confirmable: “From 7 PM to 8 PM I was on a video call with a customer from home.” [interview_sam:L6]: No record places Sam Whitfield on the premises during the claimed time (last seen leaving: badge_log:L5). The records cannot confirm they were at home.
Statements that records can't confirm could still be false.

Evidence:
  [statement] “I left at 6:40 PM.” [interview_sam:L2]
  [record] “2026-03-12 18:40 | Sam Whitfield | Main Entrance | EXIT” [badge_log:L5]
  [statement] “From 7 PM to 8 PM I was on a video call with a customer from home.” [interview_sam:L6]
```

## Where was Marcus at 19:45?

```
At 19:45 on 03-12, the records put Marcus Hale on the premises.
- Record 19:41: Main Entrance [badge_log:L6]
- Record 19:44: Design Lab [badge_log:L7]
- Assumption: an unnamed person on CCTV at 19:40 is probably Marcus Hale (Only Marcus Hale has a record within 5 min of this sighting (badge_log:L6, badge_log:L7). Assumed, not identified: the face is not described.)
- Assumption: an unnamed person on CCTV at 19:58 is probably Marcus Hale (This line refers back to [cctv_summary:L1], which was matched to Marcus Hale. Assumed to be the same person.)
- Marcus Hale said: “I didn't come back that night.” [interview_marcus:L2], which is contradicted by the records.

Evidence:
  [record] “2026-03-12 19:41 | Marcus Hale | Main Entrance | ENTRY” [badge_log:L6]
  [record] “2026-03-12 19:44 | Marcus Hale | Design Lab | ENTRY” [badge_log:L7]
  [assumption] “2026-03-12 19:40 | Main Entrance camera | A man in a grey hoodie carrying a black backpack enters. His face is not visible.” [cctv_summary:L1]
  [assumption] “2026-03-12 19:58 | Parking Garage camera | The same grey-hoodie figure leaves through the garage stairwell carrying the black backpack and a flat rectangular object under one arm.” [cctv_summary:L2]
  [statement] “I didn't come back that night.” [interview_marcus:L2]
```

## Who was in the Design Lab at 20:50?

```
Records put these people at Design Lab around 20:50:
- Lena Torres at 03-12 20:47 [badge_log:L9]
People who leave through an unbadged door may be missing from the records.

Evidence:
  [record] “2026-03-12 20:47 | Lena Torres | Design Lab | ENTRY” [badge_log:L9]
```

## Why not Lena?

```
Lena Torres ranks #3 of 4 with a score of -2.5.
- -1.0 fact: Alibi supported: Records show Lena Torres entering at 20:30 [badge_log:L8], 20:31 [cctv_summary:L3]; claimed 20:30.
- -1.0 fact: Alibi supported: Records put Lena Torres at Design Lab at 20:47 [badge_log:L9]; claimed ~20:45.
- -1.0 fact: Alibi supported: Records show Lena Torres leaving at 22:04 [cctv_summary:L4], 22:05 [badge_log:L10]; claimed 22:00.
- +0.5 fact: Records put Lena Torres at Design Lab at 20:47 [badge_log:L9], inside the window. They said so themselves and the records agree.
- +0.0 speculation: Priya Nair guess: "probably". Not evidence; weighs nothing.

Evidence:
  [record] “2026-03-12 20:30 | Lena Torres | Main Entrance | ENTRY” [badge_log:L8]
  [record] “2026-03-12 20:31 | Main Entrance camera | Lena Torres enters pushing a cleaning cart.” [cctv_summary:L3]
  [record] “2026-03-12 20:47 | Lena Torres | Design Lab | ENTRY” [badge_log:L9]
  [record] “2026-03-12 22:04 | Main Entrance camera | Lena Torres leaves with the cleaning cart. No bags are visible.” [cctv_summary:L4]
  [record] “2026-03-12 22:05 | Lena Torres | Main Entrance | EXIT” [badge_log:L10]
  [speculation] “Honestly, it was probably Lena.” [interview_priya:L4]
```

## What is Marcus's motive?

```
- Marcus Hale: gain (reported by Alex Brandt): "offer" [chat_marcus_alex:L1]
- Not counted: Priya Nair's guess about Marcus Hale [interview_priya:L5]

Evidence:
  [statement] “[2026-03-10 21:14] Alex Brandt: NovaForge can make you an offer, but the team wants to see the Brightwave prototype first.” [chat_marcus_alex:L1]
  [speculation] “Marcus has seemed stressed about money lately.” [interview_priya:L5]
```

## Was the drawer forced?

```
I don't have a specific rule for that question. These are the most relevant passages; no conclusion is drawn from them:

Evidence:
  [statement] “When I arrived at 8:45 the next morning, the drawer had been forced open and the laptop was gone.” [interview_daniel:L6]
  [statement] “The top drawer of Daniel's desk was already open and there was no laptop in it.” [interview_lena:L4]
  [statement] “At 6:15 PM I locked the prototype laptop in the top drawer of my desk in the Design Lab.” [interview_daniel:L2]
```

## Where was Ruth at 23:40?

```
Nobody called Ruth appears in this case, so there is no evidence about them. People in this case: Daniel Okafor, Marcus Hale, Priya Nair, Lena Torres, Sam Whitfield, Alex Brandt.
```
