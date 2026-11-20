# Evaluation output

Generated with `python evaluate.py -v`.

| Case | Difficulty | Named | Expected | Confidence | Timeline | Retrieval@5 | Invented rejected | Checks passed | Score |
|---|---|---|---|---|---|---|---|---|---|
| The Missing Prototype Laptop | easy | Marcus Hale | Marcus Hale | high | 100% | 100% | 100% | 35/35 | 100% |
| The Gallery Switch | twisted | Victor Lane | Victor Lane | high | 100% | 100% | 100% | 37/37 | 100% |
| The Leaked Formula | impossible | Noah Fisk | Noah Fisk | medium | 100% | 100% | 100% | 37/37 | 100% |

Culprit named correctly in 3/3 cases; 109/109 checks passed (100%).

The Missing Prototype Laptop:
  [PASS] names the culprit (named Marcus Hale)
  [PASS] confidence is not low (confidence high)
  [PASS] catches lie by Marcus Hale: “I didn't come back that night.”
  [PASS] catches lie by Marcus Hale: “I've never talked to anyone there.”
  [PASS] Priya Nair's alibi is not broken (status holds)
  [PASS] Lena Torres's alibi is not broken (status holds)
  [PASS] Sam Whitfield's alibi is not broken (status holds)
  [PASS] red herring Lena Torres scores below the culprit (-2.5)
  [PASS] red herring Sam Whitfield scores below the culprit (-0.5)
  [PASS] speculation flagged
  [PASS] motives of Marcus Hale
  [PASS] motives of Sam Whitfield
  [PASS] motives of Priya Nair
  [PASS] motives of Lena Torres
  [PASS] CCTV matches
  [PASS] hidden connections
  [PASS] opportunity of Marcus Hale is 'at scene' (got 'at scene')
  [PASS] opportunity of Lena Torres is 'at scene' (got 'at scene')
  [PASS] opportunity of Sam Whitfield is 'on site' (got 'on site')
  [PASS] opportunity of Priya Nair is 'no recorded presence' (got 'no recorded presence')
  [PASS] timeline has 2026-03-12 18:00 Marcus Hale [interview_marcus]
  [PASS] timeline has 2026-03-12 18:02 Marcus Hale [badge_log]
  [PASS] timeline has 2026-03-12 18:15 Daniel Okafor [interview_daniel]
  [PASS] timeline has 2026-03-12 19:40 unidentified person [cctv_summary]
  [PASS] timeline has 2026-03-12 19:41 Marcus Hale [badge_log]
  [PASS] timeline has 2026-03-12 19:44 Marcus Hale [badge_log]
  [PASS] timeline has 2026-03-12 19:58 unidentified person [cctv_summary]
  [PASS] timeline has 2026-03-12 20:47 Lena Torres [badge_log]
  [PASS] timeline has 2026-03-13 08:45 Daniel Okafor [interview_daniel]
  [PASS] search finds badge_log in the top 5 for “Marcus Hale re-entered at 19:41 (Main Entrance) and 19:44 (Design Lab).” (top 5: ['badge_log', 'badge_log', 'cctv_summary', 'badge_log', 'case_brief'])
  [PASS] search finds cctv_summary in the top 5 for “A grey-hoodie figure left via the garage stairwell at 19:58 carrying a flat rectangular object.” (top 5: ['cctv_summary', 'cctv_summary', 'case_brief', 'interview_lena', 'interview_sam'])
  [PASS] search finds chat_marcus_alex in the top 5 for “Marcus discussed handing the prototype to NovaForge and agreed to Thursday evening.” (top 5: ['interview_priya', 'interview_sam', 'interview_marcus', 'chat_marcus_alex', 'interview_sam'])
  [PASS] every invented item is rejected (30/30)
  [PASS] every genuine item is accepted (30/30)
  [PASS] every report citation matches its source (77 quoted, 18 references)

The Gallery Switch:
  [PASS] names the culprit (named Victor Lane)
  [PASS] confidence is not low (confidence high)
  [PASS] catches lie by Victor Lane: “I was at Celia's flat from 8 PM until midnight, watching the match.”
  [PASS] catches lie by Celia Ward: “Victor was with me at my flat from 8 PM until midnight.”
  [PASS] catches lie by Victor Lane: “I've never spoken to him.”
  [PASS] Omar Haddad's alibi is not broken (status holds)
  [PASS] Lucy Tran's alibi is not broken (status holds)
  [PASS] Ben Price's alibi is not broken (status holds)
  [PASS] red herring Omar Haddad scores below the culprit (-1.0)
  [PASS] disputed records
  [PASS] statement conflict about Victor Lane resolved in favour of Ben Price
  [PASS] speculation flagged
  [PASS] motives of Victor Lane
  [PASS] motives of Omar Haddad
  [PASS] motives of Lucy Tran
  [PASS] motives of Ben Price
  [PASS] CCTV matches
  [PASS] hidden connections
  [PASS] opportunity of Victor Lane is 'on site' (got 'on site')
  [PASS] opportunity of Omar Haddad is 'on site' (got 'on site')
  [PASS] opportunity of Ben Price is 'on site' (got 'on site')
  [PASS] opportunity of Lucy Tran is 'no recorded presence' (got 'no recorded presence')
  [PASS] timeline has 2026-09-18 18:30 Victor Lane [badge_log]
  [PASS] timeline has 2026-09-18 20:00 Victor Lane [interview_victor]
  [PASS] timeline has 2026-09-18 21:04 Victor Lane [wifi_log]
  [PASS] timeline has 2026-09-18 21:05 Ben Price [interview_ben]
  [PASS] timeline has 2026-09-18 21:06 unidentified person [cctv]
  [PASS] timeline has 2026-09-18 21:10 Omar Haddad [badge_log]
  [PASS] timeline has 2026-09-18 21:13 Omar Haddad [cctv]
  [PASS] timeline has 2026-09-19 09:05 Margot Ellis [brief]
  [PASS] search finds wifi_log in the top 5 for “Victor Lane's phone joined the gallery guest Wi-Fi at the Side Door at 21:04.” (top 5: ['wifi_log', 'interview_ben', 'cctv', 'chat_victor_felix', 'brief'])
  [PASS] search finds cctv in the top 5 for “CCTV shows Omar Haddad at the front desk at 21:13, three minutes after his badge opened the Vault Room.” (top 5: ['cctv', 'interview_lucy', 'badge_log', 'interview_omar', 'interview_omar'])
  [PASS] search finds chat_victor_felix in the top 5 for “Felix Moreau offered Victor 200,000 for the real Harbour at Dusk if a copy was left in its place.” (top 5: ['chat_victor_felix', 'interview_victor', 'chat_victor_felix', 'interview_ben', 'interview_margot'])
  [PASS] search finds interview_ben in the top 5 for “Ben saw Victor near the side door around 9:05 PM.” (top 5: ['interview_ben', 'interview_omar', 'brief', 'wifi_log', 'interview_omar'])
  [PASS] every invented item is rejected (30/30)
  [PASS] every genuine item is accepted (30/30)
  [PASS] every report citation matches its source (84 quoted, 25 references)

The Leaked Formula:
  [PASS] names the culprit (named Noah Fisk)
  [PASS] confidence is not low (confidence medium)
  [PASS] early evidence points to the expected wrong lead (stage 1 named Iris Kemp)
  [PASS] catches lie by Noah Fisk: “I've never spoken to anyone at Veltrix.”
  [PASS] Iris Kemp's alibi is not broken (status holds)
  [PASS] Paul Ortega's alibi is not broken (status holds)
  [PASS] Zara Quinn's alibi is not broken (status holds)
  [PASS] red herring Iris Kemp scores below the culprit (-0.5)
  [PASS] red herring Zara Quinn scores below the culprit (-1.0)
  [PASS] disputed records
  [PASS] speculation flagged
  [PASS] motives of Noah Fisk
  [PASS] motives of Iris Kemp
  [PASS] motives of Paul Ortega
  [PASS] motives of Zara Quinn
  [PASS] CCTV matches
  [PASS] hidden connections
  [PASS] opportunity of Noah Fisk is 'at scene' (got 'at scene')
  [PASS] opportunity of Iris Kemp is 'on site' (got 'on site')
  [PASS] opportunity of Paul Ortega is 'on site' (got 'on site')
  [PASS] opportunity of Zara Quinn is 'on site' (got 'on site')
  [PASS] timeline has 2026-10-07 21:40 Noah Fisk [badge_log]
  [PASS] timeline has 2026-10-07 21:40 Noah Fisk [interview_noah]
  [PASS] timeline has 2026-10-07 22:09 Noah Fisk [badge_log]
  [PASS] timeline has 2026-10-07 22:12 unidentified person [cctv]
  [PASS] timeline has 2026-10-07 22:15 Iris Kemp [login_log]
  [PASS] timeline has 2026-10-07 22:15 Iris Kemp [interview_iris]
  [PASS] timeline has 2026-10-07 22:18 Iris Kemp [badge_log]
  [PASS] timeline has 2026-10-07 22:19 Iris Kemp [cctv]
  [PASS] timeline has 2026-10-08 09:30 unidentified person [brief]
  [PASS] search finds login_log in the top 5 for “Iris Kemp's account logged in to Lab Terminal 3 and downloaded the formula at 22:15.” (top 5: ['login_log', 'interview_iris', 'brief', 'interview_iris', 'interview_noah'])
  [PASS] search finds cctv in the top 5 for “A person sat at Lab Terminal 3 at 22:12 while Iris Kemp was seen in the car park at 22:19.” (top 5: ['cctv', 'cctv', 'login_log', 'badge_log', 'interview_noah'])
  [PASS] search finds chat_noah_rhea in the top 5 for “Rhea Vance of Veltrix offered Noah 50,000 for the formula, and Noah needed money for his debts.” (top 5: ['chat_noah_rhea', 'chat_noah_rhea', 'badge_log', 'badge_log', 'badge_log'])
  [PASS] search finds badge_log in the top 5 for “Noah Fisk badged into the Lab Wing at 22:09.” (top 5: ['badge_log', 'badge_log', 'chat_noah_rhea', 'cctv', 'brief'])
  [PASS] every invented item is rejected (32/32)
  [PASS] every genuine item is accepted (30/30)
  [PASS] every report citation matches its source (51 quoted, 14 references)
