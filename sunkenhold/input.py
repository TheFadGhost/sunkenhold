"""Keyboard input: blocking reads decoded to logical key names."""
import os
import sys
import time

_SPECIALS_WIN = {
    "H": "up", "P": "down", "K": "left", "M": "right",
    "G": "home", "O": "end", "I": "pgup", "Q": "pgdn",
    "R": "insert", "S": "delete",
}
_SPECIALS_POSIX = {
    "A": "up", "B": "down", "D": "left", "C": "right",
    "H": "home", "F": "end", "5~": "pgup", "6~": "pgdn",
    "1~": "home", "4~": "end", "2~": "insert", "3~": "delete",
}
_NAMED = {"\r": "enter", "\n": "enter", "\x1b": "escape", "\t": "tab",
          "\x7f": "backspace", "\b": "backspace"}


def _read_posix_block():
    import select
    data = sys.stdin.read(1)
    if data != "\x1b":
        return data
    dr, _, _ = select.select([sys.stdin], [], [], 0.02)
    if not dr:
        return "escape"
    seq = sys.stdin.read(1)
    if seq == "[":
        rest = ""
        while True:
            dr, _, _ = select.select([sys.stdin], [], [], 0.02)
            if not dr:
                break
            ch = sys.stdin.read(1)
            rest += ch
            if ch.isalpha() or ch == "~":
                break
        return _SPECIALS_POSIX.get(rest, "unknown")
    if seq == "O":
        ch = sys.stdin.read(1)
        return _SPECIALS_POSIX.get(ch, "unknown")
    return "unknown"


def read_key(idle_fn=None):
    """Block until a key is pressed; returns a logical key name.
    idle_fn is polled every ~100ms while waiting (used for resize checks)."""
    while True:
        if os.name == "nt":
            import msvcrt
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):
                    code = msvcrt.getwch()
                    return _SPECIALS_WIN.get(code, "unknown")
                return _NAMED.get(ch, ch)
        else:
            import select
            dr, _, _ = select.select([sys.stdin], [], [], 0)
            if dr:
                k = _read_posix_block()
                if k and k != "unknown":
                    return k
                elif k == "unknown":
                    continue
        if idle_fn is not None:
            idle_fn()
        time.sleep(0.05)


