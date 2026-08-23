"""Terminal bootstrap/restore for Windows and POSIX."""
import atexit
import os
import signal
import sys


class TermCap:
    def __init__(self):
        self._posix_saved = None
        self.enabled_vt = False
        self._entered = False
        self._exited = False

    def enter(self):
        if self._entered:
            return True
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        if os.name == "nt":
            ok = self._win_enable_vt()
            if not ok:
                return False
        else:
            import tty
            import termios
            self._posix_saved = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
        self._entered = True
        atexit.register(self.restore)
        signal.signal(signal.SIGINT, self._on_signal)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, self._on_signal)
        return True

    def _win_enable_vt(self):
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            h = k32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if not k32.GetConsoleMode(h, ctypes.byref(mode)):
                return False
            new = mode.value | 0x0004
            if not k32.SetConsoleMode(h, new):
                return False
            self.enabled_vt = True
            return True
        except Exception:
            return False

    def _on_signal(self, signum, frame):
        self.restore()
        raise SystemExit(130)

    def restore(self):
        if self._exited:
            return
        self._exited = True
        sys.__stdout__.write("\x1b[?1049l\x1b[0m\x1b[?25h")
        sys.__stdout__.flush()
        if os.name != "nt" and self._posix_saved is not None:
            import termios
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN,
                                  self._posix_saved)
            except Exception:
                pass


TERM = TermCap()
