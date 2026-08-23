"""Overlay screens shared by the interactive app."""
from . import combat, content as C, items as I, progression as PROG
from . import themes as TH

LETTERS = "abcdefghijklmnopqrstuvwxyz"


def box(scr, lay, title, lines, sel=None):
    mx0 = lay["map"][0] + 1
    my0 = lay["map"][1]
    w = min(max([len(t) for t in lines] + [len(title)]) + 4,
            lay["map"][2] - 2)
    h = min(len(lines) + 2, lay["map"][3])
    for row in range(h):
        edge = "|" if 0 < row < h - 1 else "+"
        scr.put(mx0, my0 + row, edge, TH.T.UI_BORDER)
        scr.put(mx0 + w - 1, my0 + row, edge, TH.T.UI_BORDER)
        fill = "-" if row in (0, h - 1) else " "
        for col in range(1, w - 1):
            scr.put(mx0 + col, my0 + row, fill, TH.T.UI_BORDER)
    scr.text(mx0 + 2, my0, title[:w - 4], TH.T.UI_TITLE, bold=True)
    for i, line in enumerate(lines[:h - 2]):
        tok = TH.T.LOG_NEUTRAL
        bold = False
        if sel is not None and i == sel:
            tok = TH.T.UI_TITLE
            bold = True
        scr.text(mx0 + 2, my0 + 1 + i, line[:w - 4], tok, bold=bold)


def help_lines(bindings):
    out = ["Sunkenhold keys", ""]
    for cmd, desc in [
        ("wait", "pass a turn"), ("rest", "rest until healed"),
        ("pickup", "take items here"), ("descend", "stairs down"),
        ("ascend", "stairs up / win at floor 1"),
        ("inventory", "backpack"), ("character", "stats and memory"),
        ("look", "examine tiles"), ("fire", "shoot bow"),
        ("explore", "auto-explore"), ("travel", "travel to tile"),
        ("history", "message history"),
        ("save_quit", "save and exit"),
        ("quit_menu", "menu or cancel"),
    ]:
        out.append(f"  {bindings.primary(cmd):>8}  {desc}")
    out.append("  move     hjklyubn or arrows")
    out.append("  ?        this help")
    return out


def inventory_lines(game):
    p = game.player
    out = []
    for slot in ("weapon", "shield", "armour", "charm"):
        it = p.equipment.get(slot)
        nm = I.display_name(game.state, it) if it else "- empty -"
        cur = " [cursed]" if it and it.cursed else ""
        out.append(f"{slot:>7}: {nm}{cur}")
    out.append("")
    if not p.inventory:
        out.append("(pack is empty)")
    for idx, it in enumerate(p.inventory):
        letter = LETTERS[idx]
        out.append(f"{letter}) {I.display_name(game.state, it)} -- "
                   f"{I.describe(game.state, it)}")
    return out


def item_verbs(item):
    v = []
    if item.category == I.CAT_POTION:
        v.append("quaff")
    elif item.category == I.CAT_SCROLL:
        v.append("read")
    elif item.category == I.CAT_WAND:
        v.append("zap")
    elif item.category in (I.CAT_WEAPON, I.CAT_RANGED, I.CAT_ARMOUR,
                           I.CAT_CHARM):
        v.append("equip")
    v.append("drop")
    return v


def character_lines(game):
    p = game.player
    st = game.state.stats
    mem = getattr(game.state, "memory", {})
    out = [
        f"Level {p.level} delver   HP {p.hp}/{p.max_hp}",
        f"accuracy {combat.player_accuracy(game)}  evasion "
        f"{combat.player_evasion(game)}  absorb {combat.player_absorb(game)}",
        f"speed {p.base_speed}  sight {game.eff_sight()}  crit "
        f"{combat.player_crit_chance(game)}%",
        f"XP {p.xp}/{combat.xp_needed(p.level)}",
        "",
        "traits: " + (", ".join(
            PROG.LEVELUP_TEXT[t][0] for t in p.flags.get("traits", []))
            or "none yet"),
        "",
        f"kills {st['kills']}  damage dealt {st['damage_dealt']}  taken "
        f"{st['damage_taken']}",
        f"deepest floor {st['deepest']}  salvage {st['salvage']}",
        "",
        "creatures you have met:",
    ]
    for key in sorted(mem):
        e = mem[key]
        hint = C.MONSTER_MEMORY_HINTS.get(key, "")
        out.append(f"  {C.SPECIES[key].name}: seen {e['seen']}, slain "
                   f"{e['killed']}. {hint}")
    return out
