# Adding evidence: a hypothetical badge record for Sam (Case 1)

Generated with `python -m detective reassess cases/case1_missing_laptop --add samples/new_evidence/case1_sam_returns.txt`. The record is hypothetical: it shows how the system reacts when new evidence breaks an alibi.

```
New evidence (1 document):
  + badge_log_annex (badge_log): Badge reader export - Design Lab side door (found later, hypothetical)

The conclusion holds: Marcus Hale (confidence high -> high).

  Suspect              before   after   change
  Marcus Hale           +11.5   +11.5    +0.0
  Sam Whitfield          -0.5    +6.0    +6.5
  Lena Torres            -2.5    -2.5    +0.0
  Priya Nair             -3.0    -3.0    +0.0

  Sam Whitfield:
    - no longer counted (-1.0): Alibi supported: Records show Sam Whitfield leaving at 18:40 [badge_log:L5]; claimed 18:40.
    - no longer counted (-0.5): Alibi consistent, not confirmed: No record places Sam Whitfield on the premises during the claimed time (last seen leaving: badge_log:L5). The records cannot confirm they were at home.
    + new (+3.0): Alibi contradicted: Claims to be at home from 19:00 to 03-12 20:00, but records put them at Main Entrance at 19:50 [badge_log_annex:L1].
    + new (+2.0): Records put Sam Whitfield at Design Lab at 19:52 [badge_log_annex:L2], inside the window. They never mentioned it.

  New contradiction: Claims to be at home from 19:00 to 03-12 20:00, but records put them at Main Entrance at 19:50 [badge_log_annex:L1].

```
