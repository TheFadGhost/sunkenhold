# Sunkenhold — Audit Record

Audits performed before the v0.2.0 release by sub-agents that did not write
the audited code. Every HIGH/MED finding was fixed and the full suite plus
the recorded winning replay re-run afterwards.

## 1. Design audit (vs DESIGN.md)

Checks passed outright: token completeness (35/35 tokens in all four themes),
monochrome distinguishability mechanics, message-log voice (no `!`, no emoji,
no ALL-CAPS, terse past-tense), monster glyph uniqueness.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | HIGH | Ember vent glyph `*` collided with salvage; identical in monochrome | Vent remapped to `%` |
| 2 | HIGH | Overlay box truncated selectable inventory rows at 80x24 | Box now scrolls around the selection (+offset shown in title) |
| 3 | MED-HIGH | Sidebar could overwrite log rows | Sidebar writes clamped above the log strip |
| 4 | MED | Drop message leaked internal item keys | Uses display name |
| 5 | MED | History advertised a phantom PgUp binding | Binding removed; Ctrl+P is canonical |
| 6 | MED | Help omitted close_door; help list hand-duplicated | Help generated from the single COMMAND_HELP table |
| 7 | MED | contrast/safe16 FLOOR token was pure black on dark terminals | Dark grey in both themes |
| 8 | MED | Magic mapping revealed live item positions through unexplored space | Remembered tiles render a last-seen snapshot (`items_seen`), persisted in saves |
| 9-11 | LOW-MED | Layout off-by-one vs doc, log width under sidebar, cursor guard shape | Log capped at gutter; guard fixed; DESIGN.md wording corrected (map bottom row doubles as prompt strip) |
| 12-14 | LOW/INFO | Bow/arrow colour edge case (documented), doc token drift, thrall row missing from doc | Ammo uses SALVAGE token; DESIGN.md updated |

Post-fix verification: full test suite green (55 tests), UI smoke script over
help/look/inventory/character/history/rest/fire/pickup/stairs paths clean,
winning seed 90 replay still wins.

## 2. Content originality audit

**PASS** — every species name, memory hint, weapon/armour/charm/potion/scroll/
wand name, appearance set, scroll label set (checked against NetHack's full
label list), theme name, artefact lore line, boss telegraph, death-cause
strings and flavour lines are original writing. No trademarked material, real
persons, slurs or profanity. Standing notes: never shorten "the Collapsed
Vaults" to "the Vaults"; keep future charm names off Brogue's charm roster.

## 3. Code quality audit

Categories clean: no global `random` outside rng.py (determinism contract
enforced), no unbounded game-logic loops, no mutable default arguments, no
file-handle leaks.

Fixed findings:

- HIGH — bot anti-dither guard computed an alternate step but never used it;
  now returns the replacement step.
- MED — string seeds hashed with Python's randomized `hash()`; replaced with
  SHA-256 derivation so typed seeds replay identically everywhere.
- MED — parallel simulation failures fell back to serial silently; now warn.
- MED — `--unicode` flag was dead; ascii_mode threaded into terrain glyphs.
- MED + LOW — removed dead functions (`clear_movement_blockers`, `get_dist`,
  `_cat_of`, `keys_for`, `KEY_NAMES`, `FAMILIES`, `species_letter`,
  `monster_glyph`), unused imports across seven modules, a shadowed re-import,
  three no-op branches/statements, and constant parameters
  (`silent_miss`, `target_pos`, `fallback`).

Deferred (accepted, documented): config-file parse errors still fall back to
defaults without notice (defaults are safe; corrupt file preserved untouched).

## 4. Balance audit

From `baselines.json` (greedy bot, seeds 1–200, 15k-turn cap): win rate 0.5%,
median depth 6, mean 5.97, floors-1–2 death share 0%, zero crashes, zero
softlocks. Seed 90 demonstrated complete playthrough asserted in
`tests/test_sim.py`. The WIN_GATE statistical check remains opt-in via env var
so the default suite stays deterministic.

## 5. Re-audit (post-fix verification)

An independent re-check confirmed all eleven design findings FIXED with
correct line-level evidence and no new defects in the touched code paths.
Three nits from the re-check were fixed in the same pass: a dead `elif` left
in `refresh_vision`, the item-menu highlight offset (selection now lands on
verb rows), and inventory pagination (`-`/`+`) so pack entries beyond one
screen are never selectable-but-invisible. A residual cosmetic `_pretty`
branch for a removed phantom binding was also deleted.

Clean-room verification: fresh `git clone`, `pip install .`,
`sunkenhold --version`, full suite green, seed-90 replay wins.

## Verdict

Zero open findings. v1.0.0 tagged.
