# Sunkenhold — Feature Plan

Core contract (from MISSION): 12 procedurally generated floors, energy/speed turn
engine, shadowcasting FOV with memory, melee/ranged combat with stated formulas,
five status effects, unidentified items identified by use, cursed gear, level-up
choices (pick 1 of 3), permadeath with morgue + seed, versioned single-slot save
deleted on load, win condition = retrieve the Tideglass Heart from floor 12 and
carry it back to the floor 1 exit.

## Accepted (first-class features under the same build/audit loop)

| Feature | Reason |
|---|---|
| First-floor tutorial hints | Cheap contextual lines teach energy/targeting; players bounce off unexplained systems. |
| Auto-explore (`o`) | Standard QoL; hard-stops on any seen monster/item/stair so it never walks you into death. |
| Travel-to-point (`t` + look cursor) | Nearly free once explore pathing exists; kills backtracking tedium on the return trip. |
| Look/examine mode (`x`) | Load-bearing for targeting and glyph disambiguation; trivial scope. |
| Honest item descriptions | Exact stated mechanics ("+1, absorbs 2"); vagueness reads as hiding bad design. |
| Narrow confirmations | Only quit-without-save and visibly lethal terrain confirm; unknown potions stay unconfirmed (risk is the game). |
| Wizard mode behind `--wizard` flag | Invisible in normal play; essential for testing seeds/spawns/FOV. Not scored, not saved to morgue as a legit win. |
| Terminal size enforcement | Below 80x24: clear refusal message, clean restore; never a corrupted display. |
| Colourblind-safe themes + ASCII-only glyph mode | Glyph encodes category, so monochrome play is complete; ASCII fallback table for odd terminals. |
| Run statistics + summary screen | Kills/turns/damage/depth off existing counters; losses become lessons. Free aggregation. |
| Rest command (`R`) | Explicit turn economy verb; interrupts on enemy sight, damage, status, spawn notice. Replaces 400x keyrepeat. |
| Message history (`PgUp`/`^P`) | Scrolled-away messages cause perceived unfair deaths; ring buffer + overlay viewer. |
| Ranged targeting UI (`f`, Tab cycles) | Melee+ranged core is unplayable without it; bounded: visible targets only, Esc cancels. |
| Monster memory | Compounds identification loop; tactics reward attention. Small per-species dict. |
| Doors (open/close, monsters open) | Highest depth-per-line in genre: LOS breaks, funnels, safe rest spots. |
| Traps (reuse status system) | Hidden-tile paranoia nearly free via existing status engine. Visible once discovered. |
| Finite bow ammo | Prevents infinite-kite degeneracy; stacks, auto-pickup. |
| Wands with fixed charges | Deterministic resource math is simulatable and plan-around-able. |
| Identify-by-use, per-seed appearances | Gamble tension with tiny UI; `known[]` set persisted in run state. |
| Cursed unequip rule + remove-curse scroll | A curse without an unlock rule is decorative. |
| Wanderer spawns on occupied floors | Anti-stair-scum/anti-camp pressure: first spawn >=60 turns, interval shrinks with depth, cap per floor, never inside player FOV. |
| Slow gated natural regen | Regen pauses 8 turns after taking damage; rest-vs-push is a designed tradeoff. (Hunger rejected; this replaces its pacing role.) |
| Persistent remembered floors | The win condition requires re-crossing floors 11..1; regenerating them breaks the game. |
| Help screen generated from binding table | Single source of truth kills doc rot. |
| Title screen high scores from morgue + seed entry | Reuses morgue; seed entry makes bug reports reproducible. Blank = random. |
| Quit menu confirm on Esc | Esc is also cancel; one reusable modal prevents accidental death-by-Esc. |
| Salvage (score treasure, auto-pickup) | Gold without a shop needs a purpose; score-bearing pickup, weighted by max depth. |
| Single boss on floor 12 | Payoff for the fetch quest; reuses statuses/summons; extra energy income hard-capped. |
| Transparent score formula | depth-weighted kills+salvage+artefact−turn drag; excludes bonus-spawn kills to prevent farming inversions. |

## Rejected

| Feature | Reason |
|---|---|
| Hunger/food clock | Rage-generator on the mandatory 12->1 return trip; pacing handled by spawns+regen instead. |
| Torch fuel as second upkeep clock | Doubles tuning surface; scarcity folded into ammo/potions only. |
| Full noise-propagation stealth | Big test burden, marginal depth; combat simply wakes monsters within radius. |
| Static shops / economy | Second product; salvage is score-only. |
| Gold with no sink | Dead weight — replaced by score-bearing salvage. |
| Weight-based encumbrance | Tedium multiplier; slot caps preserve the real decision. |
| Thrown items | Ranged niche already occupied by bow+wands; breakage rules add surface, not depth. |
| Identify-scroll economy / price-ID meta | Second product inside identification. |
| Random wand recharge | Unbalanceable variance; fixed charges instead. |
| Post-win difficulty modifiers | Zero pre-win value; config surface most runs never see. Deferred past 1.0. |
| Cross-run corpse retrieval | Contradicts permadeath; invites death-farming. |
| Minimap at large sizes | Second renderer/layout system; defer post-1.0. |
| Mouse support | Flaky cross-terminal reporting; keyboard travel covers it. Keyboard-native product. |
| Overworld/towns/quests, crafting, tileset renderer, multiplayer, meta-progression, day-night, terminal bell, bracketed paste | Second products or noise; outside the dungeon-crawl core. |

## Exploit controls (design commitments)

1. **Regen gating**: no healing while in combat-visible threat; 8-turn calm timer;
   resting interrupted by any seen enemy, damage, or new spawn message.
2. **Wanderer pressure**: per-floor timer ticks only while the player occupies the
   floor; never spawns within player FOV; cap 6 bonus spawns/floor.
3. **Save discipline**: autosave on floor transition only; load consumes the slot;
   death deletes the slot; state digest stored to detect tampering/corruption.

## Clock basis decision (from red-flag review)

All timers (regen calm counter, wanderer spawn clocks, status durations, boss
telegraphs) tick on **energy consumed** (i.e., resolved actor turns), not wall
turns, so slow/haste cannot warp pacing invisibly.

## Balance targets (simulated, recorded in baselines.json)

- Greedy headless bot win rate 5–15%; median depth reached 5–7.
- Early-game (floors 1–2) death share < 35% of runs.
- Starvation-equivalent degenerate deaths: none (no hunger system).
- Kiting dominance check: ranged kill share < 50% of bot kills.
