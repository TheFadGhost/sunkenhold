"""Interactive application: title, menus, end screens."""
import os
import time

from . import combat, content as C, items as I, morgue
from . import save as SAVE
from . import screens as SC
from . import themes as TH
from .game import Game
from .input import read_key
from .keys import Bindings
from .render import Screen
from .view import layout, draw_footer


class App:
    def __init__(self, cfg, data_dir, seed=None, wizard=False,
                 mono=None, theme=None):
        self.cfg = cfg
        self.data_dir = data_dir
        self.wizard = wizard
        self.bindings = Bindings(cfg.get("keys"))
        self.save_path = os.path.join(data_dir, "run.save")
        self.morgue_path = os.path.join(data_dir, "morgue.jsonl")
        self.scr = Screen(theme or cfg.get("theme", "classic"), mono=mono,
                          ascii_mode=cfg.get("ascii", True))
        self.seed_arg = seed
        self.game = None

    # ---------- helpers ----------

    def _lay(self):
        return layout(self.scr)

    def _guard_size(self):
        while True:
            ok, w, h = self.scr.fits()
            if ok:
                return
            self.scr.clear()
            msg = f"Sunkenhold needs {self.scr.w}x{self.scr.h} or larger."
            self.scr.text((w - len(msg)) // 2, h // 2, msg, TH.T.UI_TITLE)
            self.scr.text((w - 24) // 2, h // 2 + 1,
                          "Enlarge the window to continue.",
                          TH.T.LOG_NEUTRAL)
            self.scr.flush()
            time.sleep(0.3)

    def on_idle(self):
        self._guard_size()

    def draw_play(self, extra=None, cursor=None, mode="play"):
        scr = self.scr
        scr.clear()
        lay = self._lay()
        if self.wizard:
            lv = self.game.current_level()
            for i in range(lv.w * lv.h):
                if lv.tiles[i] != 0:
                    lv.seen[i] = 1
        draw_map(scr, self.game, lay, cursor)
        draw_sidebar(scr, self.game, lay, extra)
        draw_log(scr, self.game, lay)
        draw_footer(scr, self.bindings, lay, mode)
        scr.flush()

    def _wire(self, game):
        game.autosave_fn = lambda g: SAVE.save_game(g, self.save_path)
        game.delete_save_fn = lambda: SAVE.delete_save(self.save_path)

    # ---------- title ----------

    def title(self):
        self._guard_size()
        while True:
            scr = self.scr
            scr.clear()
            lay = self._lay()
            art = ["   ____             _             _          _ ",
                   "  / ___|  ___   ___| | ___   ___ | | ___  __| |",
                   "  \\___ \\ / _ \\ / __| |/ / | | \\| |/ _ \\/ _` |",
                   "   ___) | (_) | (__|   <| |_| | |  __/ (_| |",
                   "  |____/ \\___/ \\___|_|\\_\\\\__,_|_|\\___|\\__,_|",
                   ]
            for i, ln in enumerate(art):
                scr.text(4, 2 + i, ln, TH.T.UI_TITLE, bold=True)
            has_save = os.path.exists(self.save_path)
            lines = [
                "[N]ew delve   [R]esume" + ("" if has_save else " (no save)")
                + "   [H]elp   [S]cores   [Q]uit",
            ]
            for i, ln in enumerate(lines):
                scr.text(6, 9 + i, ln, TH.T.LOG_NEUTRAL)
            recs = morgue.top_scores(self.morgue_path, 5)
            scr.text(6, 12, "Best delves:", TH.T.UI_TITLE)
            for i, r in enumerate(recs):
                tag = "won" if r.get("won") else f"died floor {r['depth']}"
                scr.text(6, 13 + i,
                         f"{r['score']:>6}  {tag:<14} cause: "
                         f"{r.get('cause','')[:40]}",
                         TH.T.LOG_NEUTRAL)
            draw_footer(scr, self.bindings, lay, "menu")
            scr.flush()
            k = read_key(self.on_idle).lower()
            if k == "q":
                return None
            if k == "h":
                self.show_help()
            elif k == "s":
                self.show_scores()
            elif k == "n":
                seed = self._ask_seed()
                if seed is None:
                    continue
                g = Game(seed, wizard=self.wizard)
                g.new_game()
                self._wire(g)
                self.game = g
                from .play import PlaySession
                return PlaySession(self)
            elif k == "r":
                try:
                    st = SAVE.load_state(self.save_path)
                except SAVE.SaveError as e:
                    self._flash(str(e))
                    continue
                SAVE.delete_save(self.save_path)
                g = Game.from_state(st, wizard=self.wizard)
                self._wire(g)
                self.game = g
                from .play import PlaySession
                return PlaySession(self)

    def _ask_seed(self):
        scr = self.scr
        scr.text(6, 11, "Seed (blank for random): ", TH.T.LOG_NEUTRAL)
        scr.flush()
        buf = ""
        while True:
            k = read_key(self.on_idle)
            if k in ("enter",):
                break
            if k == "escape":
                return None
            if k in ("backspace",):
                buf = buf[:-1]
            elif isinstance(k, str) and len(k) == 1 and (k.isalnum() or k in "-"):
                buf += k
            scr.text(32, 11, (buf[-30:] + " ").ljust(31), TH.T.LOG_NEUTRAL)
            scr.flush()
        if buf.strip() == "":
            return int.from_bytes(os.urandom(8), "little")
        try:
            return int(buf)
        except ValueError:
            return abs(hash(buf)) % (1 << 62)

    def _flash(self, msg):
        lay = self._lay()
        self.scr.text(lay["map"][0], lay["log_y0"] - 1, msg[:60],
                      TH.T.LOG_BAD, bold=True)
        self.scr.flush()
        read_key(self.on_idle)

    def show_help(self):
        scr = self.scr
        scr.clear()
        lay = self._lay()
        lines = SC.help_lines(self.bindings)
        SC.box(scr, lay, "Help", lines)
        scr.flush()
        read_key(self.on_idle)

    def show_scores(self):
        scr = self.scr
        scr.clear()
        lay = self._lay()
        recs = morgue.top_scores(self.morgue_path, 15)
        lines = ["score  result          cause / seed"]
        for r in recs:
            res = "won" if r.get("won") else f"died fl {r['depth']}"
            lines.append(f"{r['score']:>6}  {res:<14} "
                         f"{r.get('cause', '')[:30]} seed {r.get('seed')}")
        if not recs:
            lines.append("(no runs recorded yet)")
        lines.append("")
        lines.append("press any key")
        SC.box(scr, lay, "Morgue", lines)
        scr.flush()
        read_key(self.on_idle)
