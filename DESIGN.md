# Sunkenhold — Design Document

## Point of view

Sunkenhold's screen is a dense information display in the tradition of the
terminal roguelikes that have stayed readable for forty years. Every glyph is a
word in a fixed vocabulary the player learns once; every colour is an adjective,
never decoration. Clarity outranks spectacle in every decision: nothing blinks,
nothing moves on its own, no effect delays input, and the answer to "what is
that?" is always one keypress away (`x`). The register is terse, factual, and
quietly serious — a lantern-lit ledger of a drowning fortress, not a fireworks
show.

## Glyph and colour scheme

**Rule: glyph indicates category, colour indicates variant.** A player who sees
a letter knows "hostile", a punctuation mark means "thing you can pick up",
terrain uses its own set — before any colour is read at all. Colour then splits
variants inside a category (monster families, item kinds). No two commonly
co-occurring *entities* share both glyph and colour; within a category, same-glyph
items are disambiguated by look mode (`x`) and by name, which is standard practice
and why look mode exists.

### Terrain and features

| Glyph | Meaning | Notes |
|---|---|---|
| `#` | wall | blocks sight and movement |
| `.` | floor | |
| `+` | closed door | |
| `'` | open door | |
| `>` | stairs down | |
| `<` | stairs up / exit on floor 1 | |
| `^` | discovered trap | hidden traps render as plain floor until found |
| `~` | shallow water | costs 2 energy-units to enter; extinguishes burning |
| `"` | fungus patch | chance of poison spores when stepped |
| `,` | rubble | costs 1.5x movement energy |
| `%` | ember vent | may ignite the careless; glows (visible at range) |
| `&` | the Tideglass Heart | unique artefact |### Items

| Glyph | Category |
|---|---|
| `!` | potion |
| `?` | scroll |
| `/` | wand |
| `)` | melee weapon |
| `(` | bow or arrows |
| `[` | body armour or shield |
| `=` | charm (trinket slot) |
| `*` | salvage (score treasure, auto-picked) |
| `&` | artefact when lying on the floor |

Arrows share the `(` glyph with bows but use a distinct colour token, so the
most commonly co-occurring pair never matches on both channels.

Unidentified items use the neutral ITEM_UNIDENTIFIED token. After identification
they take their appearance colour — which matches the run's appearance name
("a swirling green potion") — so colour never leaks information early.

### Actors

Player is `@`. Hostiles are letters; **uppercase marks a boss**. Every species
has a distinct letter, which makes hostile entities fully distinguishable with
colour off (the deuteranopia/protanopia guarantee rests on this, not on hue).

| Glyph | Species (family → colour variant) |
|---|---|
| `g` | gnawling (beast) |
| `f` | flittermaw (beast) |
| `s` | seepslime (abomination) |
| `h` | husk (undead) |
| `r` | reedshot (ranged kiter) |
| `c` | cinder sprite (ranged, burning) |
| `d` | murk hound (pack hunter) |
| `w` | tombweaver (ambusher) |
| `p` | poolwatcher (stationary gaze) |
| `b` | barrow brute (slow tank) |
| `k` | skitterking (flees, returns with friends) |
| `t` | drowned thrall (the Warden's summon) |
| `W` | the Drowned Warden (boss, floor 12) |

Monster family colours: beast, ranged, undead, abomination, boss — five distinct
token hues per theme, chosen so any two co-occurring species on screen differ by
letter first.

## Screen layout

Fixed proportions derived from measured terminal size, never assumed:

- Sidebar: **19 columns**, right-aligned, always.
- Footer hint line: **1 row**, bottom.
- Message log: `max(4, H // 5)` rows capped at 6, directly above the footer.
- Map viewport: everything else (all columns left of the sidebar minus a 1-column
  gutter, all rows above the log).

At exactly **80x24**: map viewport 60 cols x 19 rows (its bottom row doubles
as the prompt strip for targeting/look prompts), sidebar 19 cols, log 4 rows,
footer 1 row. Nothing clips; if the measured size is smaller than
80x24 the game refuses to start (or shows an overlay on shrink mid-run) with one
clear sentence and restores the terminal cleanly. Larger terminals grow the map
viewport first, then the log; the sidebar stays 19 columns. Panels never change
position between turns. Sidebar writes are clamped above the log.

Sidebar contents (top to bottom): name and level, HP bar drawn as
`HP [####....] 12/20`, stats line, depth, active status effects with remaining
turns, equipped gear summary, and during targeting the current target's name/HP.

Footer shows context-sensitive hints, e.g.
`[arrows/hjkl] move  [i]nv  [x]look  [f]ire  [>]descend  [?]help`.

## Visibility rendering

Three states, distinguished **without relying on colour alone**:

- **Unknown**: never seen — blank space.
- **Remembered**: explored, not currently visible — same glyph, rendered with the
  SGR 2 *dim/faint* attribute in every theme including monochrome, plus each
  theme's darker token colours. Remembered tiles show terrain, discovered traps,
  and items last seen there (dim); monsters are never drawn from memory.
- **Visible**: full brightness; entities additionally render **bold** (SGR 1).

Light model: the player's lantern reveals a personal radius (`sight`, base 7).
Glowing tiles (`%` vents, `"` fungus clusters marked lit by theme) are visible
through LOS out to `sight + 2`. FOV itself is symmetric shadowcasting; what the
player can see, can see the player.

## Message log voice

Terse, factual, **past tense**. Never jokey, never exclamatory, no ALL-CAPS,
no emoji. Sentences are self-contained (screen-reader friendly) and never rely
on colour: damage numbers, statuses, and durations appear as words.

Examples:
- `You hit the gnawling for 5.`
- `The reedshot shoots you for 3. You are bleeding slowly.` (no — bleeding not in game; e.g.) `You are poisoned (6 turns).`
- `The murk hound misses you.`
- `You quaff a swirling green potion. It heals 12.`
- `The husk crumbles.`
- `You feel slower. (stunned, 3 turns)`

Repeats combine: consecutive identical messages collapse to `You hit the gnawling
for 5. (x3)`. The bottom three-to-six lines show the newest messages; `PgUp`/`^P`
opens full history, paginated, oldest first, Esc closes.

## Inventory and character screens

- **Inventory (`i`)**: overlay panel over the map area. Header lists equip slots
  (`weapon / shield / armour / charm`) showing the equipped item or `- empty -`,
  then a flat letter-indexed backpack list. Each line: letter, quantity, honest
  description with exact mechanics (`+1 short sword, 1d5+1 dmg`) or, for unknown
  consumables, appearance only. Selecting offers contextual verbs (equip/quaff/
  read/zap/drop); Esc cancels.
- **Character (`@` on inventory or `C`)**: stats, XP and next-level progress,
  traits chosen at level-up, monster memory highlights, run statistics.
- **Level-up choice**: pauses play, presents exactly three options with honest
  mechanical text; number keys choose; no time limit.

## Semantic colour tokens

Rendering code references **tokens only**; hex/palette values live exclusively in
theme tables. Tokens: `WALL FLOOR DOOR STAIRS WATER FUNGUS RUBBLE VENT TRAP
ITEM_UNID POTION SCROLL WAND WEAPON ARMOUR CHARM SALVAGE ARTEFACT MON_BEAST
MON_RANGED MON_UNDEAD MON_ABOM MON_BOSS PLAYER LOG_GOOD LOG_BAD LOG_NEUTRAL
LOG_INFO HP_OK HP_LOW STATUS_BAD STATUS_INFO UI_BORDER UI_DIM UI_TITLE`. Four
shipped themes: `classic` (dark), `paper`
(light terminals), `contrast` (high contrast), `safe16` (16-colour-safe). Every
theme keeps visible/remembered/unknown distinct (dim attribute does the heavy
lifting) and keeps hostiles identifiable at a glance. `NO_COLOR` env var or
`--mono` forces attribute-only rendering (bold/dim/inverse still allowed).

## Damage, healing and status without colour

All combat outcomes state actor, target, number, and result in words:
`for N`, `misses`, `critically ... for N`. Statuses announce apply, tick harm,
and expiry with turn counts: `You are confused (5 turns).`, `The poison wears
off.` Healing states the amount. The log alone reconstructs any fight.

## Input and responsiveness

Blocking keyboard read (zero latency, zero idle CPU); the frame redraws only when
state changes. Diff-based redraw: only changed cells are emitted, cursor moved per
run of changes; initial paint clears once. Alternate screen buffer + hidden cursor
on start; one idempotent restore path (alt-screen exit, cursor shown, SGR reset,
raw mode off) runs on normal exit, SIGINT/SIGBREAK, window close, and panic — the
panic handler restores the terminal *before* printing the traceback. Save writes
are atomic (temp file + rename) so abrupt exits cannot corrupt the slot.

## Unicode safety

Default glyph set is pure ASCII; `--unicode` swaps a few glyphs for box/water
characters. All name rendering truncates via a width-aware helper
(`unicodedata.east_asian_width`) so wide characters cannot break column layout.
stdout is reconfigured to UTF-8 with replacement on boot.

## Banned (checked at audit)

Emoji as entity glyphs, ALL-CAPS log shouting, exclamation marks in game text,
jokey flavour, decorative colour, rainbow palettes, panels shifting between turns,
any animation delaying input, colour-only information.
