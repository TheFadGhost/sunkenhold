"""The live play loop: input dispatch, targeting, look, travel, end screens."""
import datetime

from . import content as C, items as I, morgue
from . import progression as PROG
from . import save as SAVE
from . import screens as SC
from . import themes as TH
from .input import read_key
from .keys import MOVES
from .view import layout

LETTERS = SC.LETTERS


class PlaySession:
    def __init__(self, app):
        self.app = app
        self.scr = app.scr
        self.game = app.game
        self.bindings = app.bindings

    # ---------- plumbing ----------

    def lay(self):
        return layout(self.scr)

    def draw(self, extra=None, cursor=None, mode="play"):
        self.app.draw_play(extra=extra, cursor=cursor, mode=mode)

    def key(self):
        return read_key(self.app.on_idle)

    def run_world(self):
        g = self.game
        if g.pending:
            g.run_until_player_input()
        while g.player.alive and not g.victory \
                and g.player.flags.get("pending_levelups", 0) > 0:
            if not self.level_up():
                break

    # ---------- main loop ----------

    def loop(self):
        g = self.game
        try:
            while g.player.alive and not g.victory:
                self.draw()
                k = self.key()
                cmd = self.bindings.command_for(k)
                if cmd is None:
                    continue
                if cmd in MOVES:
                    dx, dy = MOVES[cmd]
                    g.act_move(dx, dy)
                    self.run_world()
                elif cmd == "wait":
                    g.act_wait()
                    self.run_world()
                elif cmd == "close_door":
                    ask = self.ask_direction("Shut which door?")
                    if ask is not None:
                        g.act_close(*ask)
                        self.run_world()
                elif cmd == "rest":
                    g.start_rest()
                    self.run_world()
                elif cmd == "pickup":
                    g.act_pickup()
                    self.run_world()
                elif cmd == "descend":
                    g.act_descend()
                    self.run_world()
                elif cmd == "ascend":
                    g.act_ascend()
                    self.run_world()
                elif cmd == "inventory":
                    self.inventory_screen()
                elif cmd == "character":
                    self.character_screen()
                elif cmd == "help":
                    self.app.show_help()
                elif cmd == "history":
                    self.history_screen()
                elif cmd == "look":
                    self.look_mode()
                elif cmd == "fire":
                    tgt = self.target_pick("Fire at")
                    if tgt is None:
                        continue
                    g.act_fire(tgt)
                    self.run_world()
                elif cmd == "explore":
                    self.auto_explore()
                elif cmd == "travel":
                    dest = self.aim_mode()
                    if dest is not None:
                        self.travel_to(dest)
                elif cmd == "wizard_reveal" and g.wizard:
                    lv = g.current_level()
                    for i in range(lv.w * lv.h):
                        if lv.tiles[i] != 0:
                            lv.seen[i] = 1
                elif cmd == "save_quit":
                    SAVE.save_game(g, self.app.save_path)
                    g.add_message("Saved. The hold waits.", "info")
                    return
                elif cmd == "quit_menu":
                    if self.quit_menu():
                        return
                if g.death_cause or g.victory:
                    self.end_run()
                    return
        finally:
            pass

    # ---------- overlays ----------

    def level_up(self):
        g = self.game
        choices = PROG.roll_levelup_choices(g.rng)
        lines = ["Choose one boon:", ""]
        for i, c in enumerate(choices):
            name, desc = PROG.LEVELUP_TEXT[c]
            lines.append(f"[{i + 1}] {name}: {desc}")
        lines.append("")
        lines.append("[esc] decide later")
        while True:
            self.draw()
            self.scr.clear()
            lay = self.lay()
            SC.box(self.scr, lay, f"Level {g.player.level}",
                   lines)
            self.draw_log_only(lay)
            self.scr.flush()
            k = self.key()
            if k in ("1", "2", "3") and int(k) <= len(choices):
                PROG.apply_levelup(g, choices[int(k) - 1])
                p = g.player
                p.flags["pending_levelups"] -= 1
                g.add_message(f"You feel changed: "
                              f"{PROG.LEVELUP_TEXT[choices[int(k) - 1]][0]}.",
                              "good")
                return True
            if k in ("escape", "enter"):
                return False

    def draw_log_only(self, lay):
        from .view import draw_log
        draw_log(self.scr, self.game, lay)

    def inventory_screen(self):
        g = self.game
        page = 0

        def per_page():
            lay = self.lay()
            return max(1, lay["map"][3] - 8)

        while True:
            scr = self.scr
            scr.clear()
            lay = self.lay()
            lines = SC.inventory_lines(g, page, per_page())
            SC.box(scr, lay, "Inventory", lines)
            self.draw_log_only(lay)
            scr.flush()
            k = self.key()
            if k in ("escape", "i"):
                return
            if k in ("+", "=", "pgdn"):
                page += 1
                continue
            if k in ("-", "pgup"):
                page = max(0, page - 1)
                continue
            start = page * per_page()
            chunk = g.player.inventory[start:start + per_page()]
            if isinstance(k, str) and k in LETTERS[:len(chunk)]:
                item = chunk[LETTERS.index(k)]
                if self.item_menu(item):
                    return

    def item_menu(self, item):
        g = self.game
        verbs = SC.item_verbs(item)
        sel = 0
        while True:
            scr = self.scr
            scr.clear()
            lay = self.lay()
            lines = [I.display_name(g.state, item),
                     I.describe(g.state, item), ""]
            lines += [f"[{i + 1}] {v}" for i, v in enumerate(verbs)]
            lines += ["[esc] back"]
            SC.box(scr, lay, "Item", lines, sel=3 + sel)
            self.draw_log_only(lay)
            scr.flush()
            k = self.key()
            if k == "escape":
                return False
            if k.isdigit() and 1 <= int(k) <= len(verbs):
                verb = verbs[int(k) - 1]
                if verb == "quaff":
                    g.act_quaff(item)
                elif verb == "read":
                    g.act_read(item)
                elif verb == "equip":
                    g.act_equip(item)
                elif verb == "drop":
                    g.act_drop(item)
                elif verb == "zap":
                    d = self.ask_direction("Zap which way?")
                    if d is None:
                        continue
                    g.act_zap(item, d)
                self.run_world()
                return True
            if k in ("up",):
                sel = max(0, sel - 1)
            if k in ("down",):
                sel = min(len(verbs), sel + 1)

    def ask_direction(self, prompt):
        while True:
            self.draw(mode="look")
            lay = self.lay()
            self.scr.text(2, lay["log_y0"] - 1, prompt, TH.T.LOG_INFO,
                          bold=True)
            self.scr.flush()
            k = self.key()
            if k == "escape":
                return None
            cmd = self.bindings.command_for(k)
            if cmd in MOVES:
                return MOVES[cmd]

    def character_screen(self):
        while True:
            scr = self.scr
            scr.clear()
            lay = self.lay()
            SC.box(scr, lay, "Character",
                   SC.character_lines(self.game)[:lay["map"][3] - 4])
            self.draw_log_only(lay)
            scr.flush()
            k = self.key()
            if k in ("escape", "C", "enter"):
                return

    def history_screen(self):
        msgs = list(self.game.state.messages)
        page = max(0, len(msgs) - 16)
        per = 16
        while True:
            scr = self.scr
            scr.clear()
            lay = self.lay()
            toktok = {"good": TH.T.LOG_GOOD, "bad": TH.T.LOG_BAD,
                      "info": TH.T.LOG_INFO, "neutral": TH.T.LOG_NEUTRAL}
            chunk = msgs[page:page + per]
            lines = [t if c <= 1 else f"{t} (x{c})"
                     for t, _, c in chunk]
            lines += ["", f"[pgup/pgdn] scroll  page {page // per + 1}/"
                          f"{max(1, (len(msgs) - 1) // per + 1)}  [esc] close"]
            SC.box(scr, lay, "Message history", lines)
            scr.flush()
            k = self.key()
            if k in ("escape", "\x10"):
                return
            if k in ("pgup", "up"):
                page = max(0, page - per)
            if k in ("pgdn", "down"):
                page = min(max(0, len(msgs) - per), page + per)

    def visible_enemies(self):
        lv = self.game.current_level()
        p = self.game.player
        out = [m for m in lv.monsters
               if m.alive and m.pos in self.game.visible]
        out.sort(key=lambda m: (abs(m.x - p.x) + abs(m.y - p.y), m.id))
        return out

    def target_pick(self, prompt):
        foes = self.visible_enemies()
        if not foes:
            self.game.add_message("No target in sight.", "neutral")
            return None
        idx = 0
        while True:
            f = foes[idx]
            info = [f"{prompt}:", C.SPECIES[f.species].name,
                    f"HP {f.hp}/{f.max_hp}",
                    "", "[tab] next  [enter] confirm  [esc] cancel"]
            self.draw(extra=info, cursor=f.pos, mode="target")
            k = self.key()
            if k == "escape":
                return None
            if k == "tab":
                idx = (idx + 1) % len(foes)
            if k in ("enter",):
                return f

    def look_mode(self):
        p = self.game.player
        cur = [p.x, p.y]
        while True:
            info = self._look_info(tuple(cur))
            self.draw(extra=info, cursor=tuple(cur), mode="look")
            k = self.key()
            if k == "escape":
                return None
            if k in ("enter",):
                return tuple(cur)
            cmd = self.bindings.command_for(k)
            if cmd in MOVES:
                dx, dy = MOVES[cmd]
                cur[0] += dx
                cur[1] += dy

    def _look_info(self, pos):
        g = self.game
        lv = g.current_level()
        if not lv.in_bounds(*pos) or lv.seen[pos[1] * lv.w + pos[0]] != 1:
            return ["unknown ground"]
        vis = pos in g.visible
        code = lv.tile(*pos)
        names = {0: "rock wall", 1: "floor", 2: "closed door",
                 3: "open door", 4: "stairs down", 5: "stairs up",
                 6: "rubble", 7: "shallow water", 8: "fungus patch",
                 9: "ember vent"}
        out = [names.get(code, "?")]
        if (pos) in lv.traps_found:
            out.append("a revealed trap")
        m = lv.monster_at(*pos) if vis else None
        if m is not None and m.alive:
            s = C.SPECIES[m.species]
            mem = getattr(g.state, "memory", {}).get(m.species, {})
            hint = C.MONSTER_MEMORY_HINTS.get(m.species, "")
            out.append(f"{s.name} HP {m.hp}/{m.max_hp}"
                       + (f" ({hint})" if mem else ""))
        for it in lv.items_at(*pos):
            out.append(I.display_name(g.state, it) + " -- "
                       + I.describe(g.state, it))
        return out

    def aim_mode(self):
        got = self.look_mode()
        return got

    def auto_explore(self):
        g = self.game
        steps = 0
        while steps < 500:
            nxt = g.explore_next()
            if nxt is None:
                break
            dx = nxt[0] - g.player.x
            dy = nxt[1] - g.player.y
            g.act_move(dx, dy)
            g.pending.extend([g._wait_once] * 0)
            g.run_until_player_input()
            steps += 1
            if g.death_cause or g.victory or g.enemies_visible():
                break
            self.draw()
        if g.death_cause or g.victory:
            self.end_run()
            return True
        return False

    def travel_to(self, dest):
        g = self.game
        steps = 0
        while steps < 500:
            nxt = g.travel_next(dest)
            if nxt is None:
                break
            g.act_move(nxt[0] - g.player.x, nxt[1] - g.player.y)
            g.run_until_player_input()
            steps += 1
            if g.death_cause or g.victory:
                break
            self.draw()
        if g.death_cause or g.victory:
            self.end_run()
            return True
        return False

    def quit_menu(self):
        opts = ["keep playing", "save and quit",
                "abandon this delve (no save change)"]
        sel = 0
        while True:
            scr = self.scr
            scr.clear()
            lay = self.lay()
            SC.box(scr, lay, "Quit?", opts, sel=sel)
            scr.flush()
            k = self.key()
            if k == "escape":
                return False
            if k == "up":
                sel = max(0, sel - 1)
            if k == "down":
                sel = min(len(opts) - 1, sel + 1)
            if k == "enter":
                if sel == 0:
                    return False
                if sel == 1:
                    SAVE.save_game(self.game, self.app.save_path)
                    return True
                if sel == 2:
                    return True

    # ---------- run end ----------

    def end_run(self):
        g = self.game
        won = bool(g.state.stats["won"])
        cause = "escaped with the Heart" if won else g.death_cause
        record = {
            "version": 3, "seed": g.seed, "won": won, "depth": g.depth,
            "cause": cause, "turns": g.state.turn,
            "score": g.score(), "kills": g.state.stats["kills"],
            "date": datetime.date.today().isoformat(),
        }
        if not g.wizard:
            morgue.append_record(self.app.morgue_path, record)
        lines = []
        if won:
            lines.append("You climb into daylight, the Heart beating green.")
            lines.append("Sunkenhold keeps its drowned halls. You keep your "
                         "life.")
        else:
            lines.append(f"You died on floor {g.depth}.")
            lines.append(f"Cause: {cause}.")
        st = g.state.stats
        lines += [
            "",
            f"score {g.score()}   kills {st['kills']}   turns "
            f"{g.state.turn}",
            f"deepest floor {st['deepest']}   salvage {st['salvage']}",
            "",
            f"seed {g.seed}",
            "(replay with: sunkenhold --seed " + str(g.seed) + ")",
            "",
            "press any key",
        ]
        while True:
            scr = self.scr
            scr.clear()
            lay = self.lay()
            SC.box(scr, lay,
                   "You win" if won else "You die", lines)
            scr.flush()
            read_key(self.app.on_idle)
            return
