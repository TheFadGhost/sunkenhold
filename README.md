# Sunkenhold

A turn-based ASCII roguelike of a drowned keep: twelve floors down, one
beating artefact, no way out but back up. For players who want a compact,
complete dungeon crawl they can actually finish.

Pure Python 3 standard library. No dependencies. Windows Terminal, modern
conhost, or any POSIX terminal.

```
                                     +.#    #.#             |Sunkenhold
                                     #.#    #.#             |Delver the lvl 2
                                     #.#    #"#             |HP 28/28
               ####                  #.#    #.#             |[########]
                ."                   #.#    #.#             |W: short bow
            "  ...                   #.#    #.#    #########|acc 4 ev 2 abs 1
              .....           ########'######'######........|Floor 3   turn 434
             ".....            ......'.+."..'.'...."....."..|
              ".....##################.######'######........|
             "......@......"..."".....".....".+....'.....<..|
            ##########################"######.######......."|
                                     #.#    #"#    #......."|
                                ######'######.#    #########
                                #...""......#.#    |
                                #........"..#+#    |
                                #......."...'.#    |
                                #.........."###    |
                                #.......!"..#       |
You hit the gnawling for 5.
The gnawling dies.
Something moves in the dark nearby.
```

*(live capture from seed 90, floor 3; colour stripped for this page)*

## Install & run

From a clone (no dependencies beyond Python itself):

```
pip install .            # provides the `sunkenhold` command
sunkenhold               # or: python -m sunkenhold
sunkenhold --seed 90     # replay a recorded run's world
sunkenhold simulate --runs 100   # headless bot batch + statistics
```

Requires Python 3.10+. On legacy Windows consoles the game enables VT
processing automatically and refuses cleanly if the terminal cannot.

## How to play

Descend twelve floors, take **the Tideglass Heart** from the Warden's vault,
and carry it back to the exit on floor 1. Death is permanent; your run is
recorded in a local morgue file with its seed so any run can be replayed.

| key | action |
|---|---|
| `h j k l y u b n` / arrows | move (diagonals included) |
| `.` | wait |
| `R` | rest until healed or interrupted |
| `g` | pick up |
| `i` | inventory (equip, quaff, read, zap, drop) |
| `f` | fire bow at a target |
| `c` | shut an adjacent open door |
| `x` | look / examine anything |
| `o` | auto-explore |
| `t` | travel to cursor |
| `>` / `<` | stairs |
| `C` | character sheet, monster memory, run stats |
| `PgUp`/`Ctrl+P` | message history |
| `?` | help (generated from this table) |
| `S` | save and quit (single slot; consumed on load) |

## Mechanics (all of it)

- **Turns**: every actor banks energy equal to its speed each tick and acts
  whenever it holds 100. Moving costs 100 (water 200, rubble 150); every other
  action costs 100. Fast actors simply act more often. Ties go player-first,
  then oldest spawn.
- **To-hit**: `75% + 5 x (accuracy - evasion)`, clamped 20–95.
- **Damage** = weapon dice + bonus − absorption, minimum 1. Criticals (5% +
  bonuses) double the roll before absorption.
- **Statuses**: poison stacks to 5 and ticks per turn; burning ticks 2;
  stun skips turns; slow halves speed; confusion scrambles movement.
  Durations refresh to max, poison adds stacks. Water quenches burning.
- **Identification**: potions, scrolls and wands have random appearances each
  run. You learn what something does by using it. Healing draughts you know
  from the start.
- **Curses**: some gear is cursed; equipping locks the slot until a
  clean-hands psalm is read. Its enchantment runs backwards.
- **Pressure**: idle floors spawn wanderers over time (never in sight, capped
  per floor). Carrying the Heart quickens them. Resting requires calm and
  stops when anything closes in.
- **Score**: salvage + 2x kills + 15x deepest floor (+400 if you escape)
  − turn/60, floored at 0.
- **Death**: permanent. The save slot is deleted. The morgue remembers.

## Balance record

Measured with the bundled greedy bot (`sunkenhold simulate`, seeds 1–200,
15k-turn cap): win rate 0.5%, median depth 6, early-game (floors 1–2) deaths
0%, zero crashes, zero soft-locks. Seed **90** is a recorded complete
playthrough (6424 turns, score 843) asserted in the test suite — full
floor-by-floor transcript in [`docs/WIN_SEED_90.md`](docs/WIN_SEED_90.md).

## Terminal requirements

80x24 minimum (smaller shows a clear message), 16 or 256 colours or none —
`NO_COLOR` gives full monochrome play; glyphs alone distinguish every threat.
Four themes: `classic`, `paper` (light terminals), `contrast`,
`safe16`. Select with `--theme` or `data/config.json`.

## Architecture note

One seeded RNG drives everything; identical seed plus identical inputs
reproduces an identical game state hash per turn (tested). Monsters share one
Dijkstra influence map rebuilt per player step; behaviours are small policies
over that map. Rendering diffs cell buffers and emits only changes.

MIT licensed. All names, text and lore are original to this project.
