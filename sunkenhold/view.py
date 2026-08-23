"""Frame composition: map viewport, sidebar, message log, footer."""
from . import combat, content as C, items as I, themes as TH
from .render import SIDEBAR_W


def layout(scr):
    log_h = max(4, min(6, scr.h // 5))
    map_h = scr.h - log_h - 2
    map_w = scr.w - SIDEBAR_W - 1
    return {"map": (0, 0, map_w, map_h),
            "sidebar_x": scr.w - SIDEBAR_W,
            "log_y0": scr.h - log_h - 1,
            "log_h": log_h,
            "footer_y": scr.h - 1}


def draw_map(scr, game, lay, cursor=None):
    lv = game.current_level()
    x0, y0, w, h = lay["map"]
    p = game.player
    camx = max(0, min(lv.w - w, p.x - w // 2))
    camy = max(0, min(lv.h - h, p.y - h // 2))
    for row in range(h):
        for col in range(w):
            mx, my = camx + col, camy + row
            if not lv.in_bounds(mx, my):
                continue
            vis = (mx, my) in game.visible
            seen = lv.seen[my * lv.w + mx] == 1
            if not vis and not seen:
                continue
            code = lv.tile(mx, my)
            dim = not vis
            bold = False
            ch = TH.tile_glyph(code, scr.ascii_mode)
            tok = TH.tile_token(code)
            if (mx, my) in lv.traps_found:
                ch, tok = "^", TH.T.TRAP
            items_here = None
            if vis:
                items_here = lv.items.get((mx, my))
            elif seen:
                items_here = getattr(lv, "items_seen", {}).get((mx, my))
            m = lv.monster_at(mx, my) if vis else None
            if m is not None and m.alive:
                s = C.SPECIES[m.species]
                ch = s.letter
                from .themes import species_token
                tok = species_token(m.species)
                bold = True
            elif items_here:
                top = items_here[-1]
                ch = I.glyph_for(top)
                tok = I.token_for(game.state, top)
            scr.put(col + x0, row + y0, ch, tok, bold=bold, dim=dim)
    px, py = p.x - camx + x0, p.y - camy + y0
    scr.put(px, py, "@", TH.T.PLAYER, bold=True)
    if cursor is not None:
        cx, cy = cursor
        col, row = cx - camx + x0, cy - camy + y0
        if x0 <= col < x0 + w and y0 <= row < y0 + h:
            old = scr.chars[row][col]
            oldt = scr.tokens[row][col]
            scr.put(col, row, old if old != " " else "X", oldt, bold=True)


def draw_sidebar(scr, game, lay, extra=None):
    sx = lay["sidebar_x"]
    max_row = lay["log_y0"] - 1
    p = game.player
    scr.text(sx, 0, "Sunkenhold".ljust(SIDEBAR_W), TH.T.UI_TITLE, bold=True)
    scr.text(sx, 1, f"Delver the lvl {p.level}".ljust(SIDEBAR_W),
             TH.T.LOG_NEUTRAL)

    hp = f"HP {p.hp}/{p.max_hp}"
    frac = p.hp / max(1, p.max_hp)
    bar_n = SIDEBAR_W - len(hp) - 3
    filled = int(round(bar_n * frac))
    bar = "[" + "#" * filled + "." * (bar_n - filled) + "]"
    tok = TH.T.HP_OK if frac > 0.35 else TH.T.HP_LOW
    scr.text(sx, 2, hp.ljust(SIDEBAR_W), TH.T.LOG_NEUTRAL)
    scr.text(sx, 3, bar.ljust(SIDEBAR_W), tok)

    wname = combat.player_weapon(game)["name"]
    scr.text(sx, 4, f"W: {wname[:SIDEBAR_W - 3]}".ljust(SIDEBAR_W),
             TH.T.LOG_NEUTRAL)
    ab = combat.player_absorb(game)
    ev = combat.player_evasion(game)
    ac = combat.player_accuracy(game)
    scr.text(sx, 5, f"acc {ac} ev {ev} abs {ab}".ljust(SIDEBAR_W),
             TH.T.LOG_NEUTRAL)
    scr.text(sx, 6, f"Floor {game.depth}   turn {game.state.turn}".ljust(
        SIDEBAR_W), TH.T.LOG_NEUTRAL)

    st = p.statuses
    row = 8
    order = ["poison", "burning", "stun", "slow", "confused",
             "might", "stone", "haste"]
    for name in order:
        if name in st and row < max_row:
            turns = st[name]["turns"]
            stacks = st[name].get("stacks", 1)
            label = f"{name} ({turns})"
            if name == "poison" and stacks > 1:
                label += f" x{stacks}"
            tok = TH.T.STATUS_BAD if name in (
                "poison", "burning", "stun", "slow", "confused") \
                else TH.T.STATUS_INFO
            scr.text(sx, row, label[:SIDEBAR_W].ljust(SIDEBAR_W), tok)
            row += 1

    if game.has_artefact() and row + 1 < max_row:
        scr.text(sx, row, "carrying:".ljust(SIDEBAR_W), TH.T.ARTEFACT)
        scr.text(sx, row + 1, "Tideglass Heart".ljust(SIDEBAR_W),
                 TH.T.ARTEFACT, bold=True)
        row += 2
    if extra:
        for line in extra:
            if row >= max_row:
                break
            scr.text(sx, row, line[:SIDEBAR_W].ljust(SIDEBAR_W),
                     TH.T.STATUS_INFO)
            row += 1


def draw_log(scr, game, lay):
    y0, hgt = lay["log_y0"], lay["log_h"]
    msgs = list(game.state.messages)[-hgt:]
    toktok = {"good": TH.T.LOG_GOOD, "bad": TH.T.LOG_BAD,
              "info": TH.T.LOG_INFO, "neutral": TH.T.LOG_NEUTRAL}
    width = lay["sidebar_x"] - 1
    for i, (text, kind, count) in enumerate(msgs):
        shown = text if count <= 1 else f"{text} (x{count})"
        shown = shown[:width]
        scr.text(0, y0 + i, shown.ljust(min(len(shown) + 1, width)),
                 toktok.get(kind, TH.T.LOG_NEUTRAL))


def draw_footer(scr, bindings, lay, mode="play"):
    hints = {
        "play": "[hjkl]move [.]wait [g]take [i]nv [f]ire [o]explore "
                "[x]look [>]down [<]up [R]est [?]help",
        "target": "[tab]cycle [enter]fire/confirm [esc]cancel",
        "look": "[hjkl]move cursor [enter]pick [esc]cancel",
        "inv": "[a-z]select [esc]close",
        "levelup": "[1-3]choose a boon",
        "menu": "[arrows]choose [enter]select [esc]quit",
        "travel": "[hjkl]aim, [enter]go, [esc]cancel",
    }
    text = hints.get(mode, hints["play"])
    scr.text(0, lay["footer_y"], (" " + text)[:scr.w - 1],
             TH.T.UI_DIM)
