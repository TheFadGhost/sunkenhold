"""ANSI diff-based renderer. Only changed cells are ever emitted."""
import os
import shutil
import sys

from .themes import get_theme, T
from .term import TERM

MIN_W, MIN_H = 80, 24
SIDEBAR_W = 19


def terminal_size():
    try:
        sz = shutil.get_terminal_size(fallback=(80, 24))
        return sz.columns, sz.lines
    except Exception:
        return 80, 24


def color_mode():
    """'none' | '16' | '256'."""
    if os.environ.get("NO_COLOR"):
        return "none"
    if os.environ.get("SUNKENHOLD_COLOR") in ("none", "16", "256"):
        return os.environ["SUNKENHOLD_COLOR"]
    if os.name == "nt":
        return "256" if TERM.enabled_vt else "none"
    term = os.environ.get("TERM", "")
    if "256color" in term or os.environ.get("COLORTERM"):
        return "256"
    return "16"


class Screen:
    def __init__(self, theme_name="classic", mono=None, ascii_mode=True):
        self.theme = get_theme(theme_name)
        self.ascii_mode = ascii_mode
        if mono is None:
            mono = color_mode() == "none"
        self.mono = mono
        cmode = "none" if mono else color_mode()
        self.cmode = cmode
        w, h = terminal_size()
        self.w, self.h = max(w, MIN_W), max(h, MIN_H)
        self.chars = [[" "] * self.w for _ in range(self.h)]
        self.tokens = [[T.FLOOR] * self.w for _ in range(self.h)]
        self.attrs = [[0] * self.w for _ in range(self.h)]
        self._prev = None
        self._last_sgr = None
        self._entered = False

    def enter(self):
        if not TERM.enter():
            raise RuntimeError("terminal does not support ANSI escape "
                               "sequences; run Sunkenhold in Windows "
                               "Terminal or another VT-capable console")
        out = sys.stdout
        out.write("\x1b[?1049h\x1b[?25l\x1b[2J")
        out.flush()
        self._entered = True

    def exit(self):
        if self._entered:
            sys.stdout.write("\x1b[?25h\x1b[?1049l\x1b[0m")
            sys.stdout.flush()
            self._entered = False

    def fits(self):
        w, h = terminal_size()
        return w >= MIN_W and h >= MIN_H, w, h

    def resize_if_needed(self):
        w, h = terminal_size()
        nw, nh = max(w, MIN_W), max(h, MIN_H)
        if (nw, nh) == (self.w, self.h):
            return False
        self.w, self.h = nw, nh
        self.chars = [[" "] * nw for _ in range(nh)]
        self.tokens = [[T.FLOOR] * nw for _ in range(nh)]
        self.attrs = [[0] * nw for _ in range(nh)]
        self._prev = None
        sys.stdout.write("\x1b[2J")
        return True

    def clear(self):
        for y in range(self.h):
            row_c = self.chars[y]
            for x in range(self.w):
                row_c[x] = " "

    def put(self, x, y, ch, token, bold=False, dim=False):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.chars[y][x] = ch
            self.tokens[y][x] = token
            self.attrs[y][x] = (1 if bold else 0) | (2 if dim else 0)

    def text(self, x, y, s, token, bold=False, dim=False, clip=True):
        for i, ch in enumerate(s):
            if clip and x + i >= self.w:
                break
            self.put(x + i, y, ch, token, bold, dim)

    def _sgr(self, token, attr):
        parts = []
        if attr & 1:
            parts.append("1")
        if attr & 2:
            parts.append("2")
        if self.cmode != "none":
            fg16, fg256 = self.theme.get(token, (7, 250))
            if self.cmode == "16":
                idx = fg16
                parts.append(str(30 + idx) if idx < 8 else str(90 + idx - 8))
            else:
                parts.append(f"38;5;{fg256}")
        if not parts:
            return ""
        return "\x1b[" + ";".join(parts) + "m"

    def flush(self):
        out = sys.stdout
        pieces = []
        if self._prev is None:
            pieces.append("\x1b[2J")
        state = {"sgr": None}

        def emit(pos, run):
            if not run:
                return
            pieces.append(f"\x1b[{pos[1] + 1};{pos[0] + 1}H")
            for ch, sgr in run:
                if sgr != state["sgr"]:
                    pieces.append(sgr)
                    state["sgr"] = sgr
                pieces.append(ch)

        run = []
        pos = None
        for y in range(self.h):
            prow_c = self._prev[0][y] if self._prev else None
            prow_t = self._prev[1][y] if self._prev else None
            prow_a = self._prev[2][y] if self._prev else None
            x = 0
            while x < self.w:
                ch, tok, at = self.chars[y][x], self.tokens[y][x], \
                    self.attrs[y][x]
                changed = True
                if prow_c is not None and x < len(prow_c):
                    changed = (prow_c[x] != ch or prow_t[x] != tok
                               or prow_a[x] != at)
                if not changed:
                    if run:
                        emit(pos, run)
                        run, pos = [], None
                    x += 1
                    continue
                if not run:
                    pos = (x, y)
                elif y != pos[1] or x != pos[0] + len(run):
                    emit(pos, run)
                    run, pos = [], None
                    pos = (x, y)
                run.append((ch, self._sgr(tok, at)))
                x += 1
            if run:
                emit(pos, run)
                run, pos = [], None
        if run:
            emit(pos, run)
        if pieces:
            pieces.append("\x1b[0m")
            out.write("".join(pieces))
            out.flush()
        self._prev = (
            [row[:] for row in self.chars],
            [row[:] for row in self.tokens],
            [row[:] for row in self.attrs],
        )
