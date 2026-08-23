# Recorded complete playthrough — seed 90

Replay: `python -m sunkenhold simulate --runs 1 --seed0 90` (or run the game
with `--seed 90` and follow the same route). Asserted deterministically in
`tests/test_sim.py::TestDemonstratedWin`. Transcript generated from the
engine itself; every number below is engine state, not prose.

```
Recorded complete playthrough - Sunkenhold seed 90
====================================================
 * floor 2 reached on turn 114 (HP 28/28, 2 kills)
 * level 2 on turn 190
 * floor 3 reached on turn 290 (HP 26/28, 7 kills)
 * level 3 on turn 459
 * floor 4 reached on turn 508 (HP 32/32, 11 kills)
 * level 4 on turn 1120
 * floor 5 reached on turn 1242 (HP 36/36, 23 kills)
 * floor 6 reached on turn 1749 (HP 36/36, 35 kills)
 * level 5 on turn 1922
 * floor 7 reached on turn 1987 (HP 36/36, 40 kills)
 * floor 8 reached on turn 2424 (HP 36/36, 48 kills)
 * floor 9 reached on turn 2744 (HP 36/36, 54 kills)
 * level 6 on turn 3226
 * floor 10 reached on turn 4131 (HP 36/36, 71 kills)
 * floor 11 reached on turn 4268 (HP 36/36, 75 kills)
 * floor 12 reached on turn 4831 (HP 36/36, 88 kills)
 * level 7 on turn 4855
 * TIDEGLASS HEART TAKEN on turn 4983 (HP 40/40)
 * floor 11 reached on turn 5035 (HP 40/40, 92 kills)
 * floor 10 reached on turn 5319 (HP 40/40, 93 kills)
 * floor 9 reached on turn 5523 (HP 40/40, 95 kills)
 * floor 8 reached on turn 5637 (HP 40/40, 95 kills)
 * floor 7 reached on turn 5849 (HP 40/40, 98 kills)
 * floor 6 reached on turn 5938 (HP 40/40, 99 kills)
 * floor 5 reached on turn 6006 (HP 40/40, 100 kills)
 * floor 4 reached on turn 6048 (HP 40/40, 100 kills)
 * floor 3 reached on turn 6120 (HP 40/40, 100 kills)
 * floor 2 reached on turn 6302 (HP 40/40, 101 kills)
 * floor 1 reached on turn 6373 (HP 40/40, 101 kills)
 * escaped to daylight on turn 6424

final: level 7, HP 40/40, kills 101, damage dealt 1162, taken 553,
salvage 168
score: 843
```

Note the shape of a winning run: a careful descent that tops up HP between
floors, a fast grab of the Heart once levelled, and an eleven-floor sprint
home that costs almost no fighting — pressure comes from the spawn clock,
not from standing battles.
