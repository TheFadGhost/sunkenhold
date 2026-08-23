"""Keybindings: single source of truth for both the help screen and input."""
import json
import os

DEFAULT_KEYS = {
    "move_up": ["k", "up"],
    "move_down": ["j", "down"],
    "move_left": ["h", "left"],
    "move_right": ["l", "right"],
    "move_ul": ["y", "home"],
    "move_ur": ["u", "pgup"],
    "move_dl": ["b", "end"],
    "move_dr": ["n", "pgdn"],
    "wait": ["."],
    "rest": ["R"],
    "close_door": ["c"],
    "pickup": ["g"],
    "descend": [">"],
    "ascend": ["<"],
    "inventory": ["i"],
    "character": ["C"],
    "help": ["?"],
    "history": ["\x10", "pgup2"],
    "look": ["x"],
    "fire": ["f"],
    "explore": ["o"],
    "travel": ["t"],
    "save_quit": ["S"],
    "quit_menu": ["escape"],
    "wizard_reveal": ["V"],
}

COMMAND_HELP = [
    ("move_*", "move one step (8 directions)"),
    ("wait", "pass a turn"),
    ("rest", "rest until healed or interrupted"),
    ("close_door", "shut an adjacent open door"),
    ("pickup", "take items under you"),
    ("descend", "go down stairs (>)"),
    ("ascend", "go up stairs (<); escape at floor 1 with the Heart"),
    ("inventory", "backpack and equipment"),
    ("character", "stats, traits, memory"),
    ("look", "examine tiles around you"),
    ("fire", "shoot your bow"),
    ("explore", "auto-explore until something appears"),
    ("travel", "travel to a chosen tile"),
    ("history", "full message history"),
    ("save_quit", "save and leave (slot consumed on load)"),
    ("quit_menu", "menu / cancel"),
]

MOVES = {
    "move_up": (0, -1), "move_down": (0, 1),
    "move_left": (-1, 0), "move_right": (1, 0),
    "move_ul": (-1, -1), "move_ur": (1, -1),
    "move_dl": (-1, 1), "move_dr": (1, 1),
}


class Bindings:
    def __init__(self, overrides=None):
        self.map = {k: list(v) for k, v in DEFAULT_KEYS.items()}
        if overrides:
            for cmd, keys in overrides.items():
                if cmd in self.map and isinstance(keys, list):
                    self.map[cmd] = [str(k) for k in keys]

    def command_for(self, key):
        for cmd, keys in self.map.items():
            if key in keys:
                return cmd
        return None

    def keys_for(self, cmd):
        out = []
        for k in self.map.get(cmd, []):
            out.append(_pretty(k))
        return ", ".join(k for k in out if k != "n/a")

    def primary(self, cmd):
        ks = self.map.get(cmd) or []
        return _pretty(ks[0]) if ks else ""


def _pretty(k):
    names = {" ": "space", "\x10": "ctrl+p", "escape": "esc",
             "enter": "enter", "tab": "tab"}
    if k == "pgup2":
        return "n/a"
    return names.get(k, k)


def load_config(data_dir):
    path = os.path.join(data_dir, "config.json")
    cfg = {"theme": "classic", "ascii": True, "keys": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            user = json.load(f)
        if isinstance(user, dict):
            if user.get("theme") in ("classic", "paper", "contrast",
                                     "safe16"):
                cfg["theme"] = user["theme"]
            cfg["ascii"] = bool(user.get("ascii", True))
            if isinstance(user.get("keys"), dict):
                cfg["keys"] = {k: v for k, v in user["keys"].items()
                               if k in DEFAULT_KEYS and isinstance(v, list)}
    except (OSError, ValueError):
        pass
    return cfg


def save_config(data_dir, cfg):
    path = os.path.join(data_dir, "config.json")
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=1)
    except OSError:
        pass
