# Follow-up questions: The Gallery Switch

Generated with `python -m detective ask cases/case2_gallery_switch "<question>"`.

## Is Celia telling the truth?

```
Yes. 1 statement by Celia Ward is contradicted by the evidence:
- “Victor was with me at my flat from 8 PM until midnight.” [interview_celia:L2]: Claims to be at Celia's flat from 20:00 to 09-19 00:00, but records put them at Side Door at 21:04 [wifi_log:L1].
A contradiction shows a statement is false; it does not by itself show why they lied.

Evidence:
  [statement] “Victor was with me at my flat from 8 PM until midnight.” [interview_celia:L2]
  [record] “2026-09-18 21:04 | Victor Lane | Side Door | phone joined GALLERY-GUEST” [wifi_log:L1]
```

## Where was Omar at 21:10?

```
At 21:10 on 09-18, the records put Omar Haddad on the premises.
- Record 21:13: Front Desk [cctv:L2]
- Set aside: a record at 21:10 is disputed and not used. Omar Haddad's credential was used at Vault Room at 21:10 [badge_log:L7], but CCTV shows Omar Haddad at Front Desk 3 min away in time [cctv:L2]. The card was used; who used it is in doubt.
- Omar Haddad said: “I was at the front desk from 9 PM to 9:30 PM watching the monitors.” [interview_omar:L4], which is supported by the records.

Evidence:
  [record] “2026-09-18 19:55 | Omar Haddad | Main Entrance | ENTRY” [badge_log:L5]
  [record] “2026-09-19 06:00 | Omar Haddad | Main Entrance | EXIT” [badge_log:L9]
  [record] “2026-09-18 21:13 | Front Desk camera | Omar Haddad sits at the front desk watching the monitors.” [cctv:L2]
  [record] “2026-09-18 21:10 | Omar Haddad | Vault Room | ENTRY” [badge_log:L7]
  [statement] “I was at the front desk from 9 PM to 9:30 PM watching the monitors.” [interview_omar:L4]
```

## Is Victor's alibi solid?

```
Victor Lane's alibi is broken: records contradict part of it:
- CONTRADICTED (given by Celia Ward): “Victor was with me at my flat from 8 PM until midnight.” [interview_celia:L2]. Claims to be at Celia's flat from 20:00 to 09-19 00:00, but records put them at Side Door at 21:04 [wifi_log:L1].
- SUPPORTED: “I left the gallery at 6:30 PM.” [interview_victor:L2]. Records show Victor Lane leaving at 18:30 [badge_log:L4]; claimed 18:30.
- CONTRADICTED: “I was at Celia's flat from 8 PM until midnight, watching the match.” [interview_victor:L4]. Claims to be at Celia's flat from 20:00 to 09-19 00:00, but records put them at Side Door at 21:04 [wifi_log:L1].

Evidence:
  [statement] “Victor was with me at my flat from 8 PM until midnight.” [interview_celia:L2]
  [record] “2026-09-18 21:04 | Victor Lane | Side Door | phone joined GALLERY-GUEST” [wifi_log:L1]
  [statement] “I left the gallery at 6:30 PM.” [interview_victor:L2]
  [record] “2026-09-18 18:30 | Victor Lane | Main Entrance | EXIT” [badge_log:L4]
  [statement] “I was at Celia's flat from 8 PM until midnight, watching the match.” [interview_victor:L4]
```

## What contradictions are there?

```
- Celia Ward: “Victor was with me at my flat from 8 PM until midnight.” [interview_celia:L2] vs records: Claims to be at Celia's flat from 20:00 to 09-19 00:00, but records put them at Side Door at 21:04 [wifi_log:L1].
- Victor Lane: “I was at Celia's flat from 8 PM until midnight, watching the match.” [interview_victor:L4] vs records: Claims to be at Celia's flat from 20:00 to 09-19 00:00, but records put them at Side Door at 21:04 [wifi_log:L1].
- Witnesses disagree: Celia Ward says Victor Lane was at Celia's flat (elsewhere Celia's flat 20:00-00:00 (per Celia Ward)) [interview_celia:L2], but Ben Price says Victor Lane was at Side Door (present Side Door ~21:05 (per Ben Price)) [interview_ben:L4]. The records back Ben Price: Celia Ward's account is contradicted by wifi_log:L1.
- Witnesses disagree: Victor Lane says they were at Celia's flat (elsewhere Celia's flat 20:00-00:00) [interview_victor:L4], but Ben Price says Victor Lane was at Side Door (present Side Door ~21:05 (per Ben Price)) [interview_ben:L4]. The records back Ben Price: Victor Lane's account is contradicted by wifi_log:L1.
- Victor Lane denied contact with Felix Moreau [interview_victor:L6], but messages show it.

Evidence:
  [statement] “Victor was with me at my flat from 8 PM until midnight.” [interview_celia:L2]
  [record] “2026-09-18 21:04 | Victor Lane | Side Door | phone joined GALLERY-GUEST” [wifi_log:L1]
  [statement] “I was at Celia's flat from 8 PM until midnight, watching the match.” [interview_victor:L4]
  [statement] “Around 9:05 PM I saw Victor near the side door.” [interview_ben:L4]
  [statement] “I've never spoken to him.” [interview_victor:L6]
  [statement] “[2026-09-15 22:40] Felix Moreau: I will pay you 200,000 for the real Harbour at Dusk. Leave a good copy in its place.” [chat_victor_felix:L1]
  [statement] “[2026-09-15 22:52] Victor Lane: The copy is ready. Friday night, after the guard's rounds.” [chat_victor_felix:L2]
```

## Who is Victor connected to?

```
- Victor Lane and outside party Felix Moreau exchange messages in chat_victor_felix. Victor Lane denied any such contact [interview_victor:L6].
- CCTV [cctv:L1] linked to Victor Lane by timing (assumption).
- CCTV [cctv:L3] linked to Victor Lane by timing (assumption).

Evidence:
  [statement] “[2026-09-15 22:40] Felix Moreau: I will pay you 200,000 for the real Harbour at Dusk. Leave a good copy in its place.” [chat_victor_felix:L1]
  [statement] “[2026-09-15 22:52] Victor Lane: The copy is ready. Friday night, after the guard's rounds.” [chat_victor_felix:L2]
  [statement] “I've never spoken to him.” [interview_victor:L6]
  [assumption] “2026-09-18 21:06 | Side Door camera | A man in a paint-stained jacket enters through the side door carrying a long flat case. His face is turned away.” [cctv:L1]
  [assumption] “2026-09-18 21:31 | Side Door camera | The same man leaves by the side door carrying the long flat case.” [cctv:L3]
```

## How confident are you?

```
Confidence: high.
- Victor Lane leads Omar Haddad by 12.5 points.
- Record-backed facts add +5.0, statements add +4.5 and assumptions add +2.0 to Victor Lane's score.
- If every assumption were wrong, the lead would be 10.5 points.
```
