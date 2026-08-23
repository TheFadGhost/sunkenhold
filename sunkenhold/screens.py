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
    body_h = h - 2
    start = 0
    if sel is not None and sel >= body_h:
        start = sel - body_h + 1
    shown = lines[start:start + body_h]
    for row in range(h):
        edge = "|" if 0 < row < h - 1 else "+"
        scr.put(mx0, my0 + row, edge, TH.T.UI_BORDER)
        scr.put(mx0 + w - 1, my0 + row, edge, TH.T.UI_BORDER)
        fill = "-" if row in (0, h - 1) else " "
        for col in range(1, w - 1):
            scr.put(mx0 + col, my0 + row, fill, TH.T.UI_BORDER)
    title_txt = title if start == 0 else f"{title} (+{start})"
    scr.text(mx0 + 2, my0, title_txt[:w - 4], TH.T.UI_TITLE, bold=True)
    for i, line in enumerate(shown):
        tok = TH.T.LOG_NEUTRAL
        bold = False
        idx = start + i
        if sel is not None and idx == sel:
            tok = TH.T.UI_TITLE
            bold = True
        scr.text(mx0 + 2, my0 + 1 + i, line[:w - 4], tok, bold=bold)


def help_lines(bindings):
    """Exactly fills an 80x24 overlay: one row per command."""
    from .keys import COMMAND_HELP
    out = []
    for cmd, desc in COMMAND_HELP:
        if cmd == "move_*":
            continue
        out.append(f"  {bindings.primary(cmd):>8}  {desc}")
    out.append("  move     hjklyubn or arrows")
    return out


def inventory_lines(game, page=0, per_page=None):
    p = game.player
    out = []
    for slot in ("weapon", "shield", "armour", "charm"):
        it = p.equipment.get(slot)
        nm = I.display_name(game.state, it) if it else "- empty -"
        cur = " [cursed]" if it and it.cursed else ""
        out.append(f"{slot:>7}: {nm}{cur}")
    out.append("")
    items = p.inventory
    if per_page is None:
        per_page = max(1, len(items))
    start = page * per_page
    chunk = items[start:start + per_page]
    if not chunk:
        out.append("(pack is empty)")
    for idx, it in enumerate(chunk):
        letter = LETTERS[(start + idx) % len(LETTERS)]
        out.append(f"{letter}) {I.display_name(game.state, it)} -- "
                   f"{I.describe(game.state, it)}")
    pages = max(1, (len(items) + per_page - 1) // per_page)
    if pages > 1:
        out.append(f"  -- page {page + 1}/{pages}: "
                   f"'-' and '+' to turn --")
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
