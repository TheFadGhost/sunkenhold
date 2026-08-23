"""Core entity model, status effects, level container, scheduler, game state."""
import hashlib
import json
from collections import deque

from .rng import RNG

NORMAL_COST = 100

T_WALL, T_FLOOR, T_DOOR_CLOSED, T_DOOR_OPEN = 0, 1, 2, 3
T_DOWN, T_UP, T_RUBBLE, T_WATER, T_FUNGUS, T_VENT = 4, 5, 6, 7, 8, 9

WALKABLE = {T_FLOOR, T_DOOR_OPEN, T_DOOR_CLOSED, T_DOWN, T_UP, T_RUBBLE,
            T_WATER, T_FUNGUS, T_VENT}
OPAQUE = {T_WALL, T_DOOR_CLOSED}
COST_MULT = {T_WATER: 2.0, T_RUBBLE: 1.5, T_DOOR_CLOSED: 2.0}

POISON, BURNING, STUN, SLOW, CONFUSED = "poison", "burning", "stun", "slow", "confused"
POISON_STACK_CAP = 5


def move_cost(tile: int) -> int:
    return int(NORMAL_COST * COST_MULT.get(tile, 1.0))


def effective_speed(actor) -> int:
    s = actor.base_speed
    st = actor.statuses
    if SLOW in st:
        s = max(30, s // 2)
    return s


class Actor:
    def __init__(self, aid=0, kind="monster", x=0, y=0, hp=10,
                 base_speed=100, acc=0, eva=0,
                 armour=0, dmg="1d3", dmg_bonus=0, crit_bonus=0, species=None,
                 sight=7):
        self.id = aid
        self.kind = kind
        self.species = species
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = hp
        self.base_speed = base_speed
        self.energy = 0
        self.acc = acc
        self.eva = eva
        self.armour = armour
        self.dmg = dmg
        self.dmg_bonus = dmg_bonus
        self.crit_bonus = crit_bonus
        self.sight = sight
        self.statuses = {}
        self.alive = True
        self.calm = 0
        self.flags = {}

    @property
    def pos(self):
        return (self.x, self.y)

    def to_dict(self):
        return {
            "id": self.id, "kind": self.kind, "species": self.species,
            "x": self.x, "y": self.y, "hp": self.hp, "max_hp": self.max_hp,
            "base_speed": self.base_speed, "energy": self.energy,
            "acc": self.acc, "eva": self.eva, "armour": self.armour,
            "dmg": self.dmg, "dmg_bonus": self.dmg_bonus,
            "crit_bonus": self.crit_bonus, "sight": self.sight,
            "statuses": self.statuses, "alive": self.alive,
            "calm": self.calm, "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d):
        a = cls(d["id"], d["kind"], d["x"], d["y"], d["hp"], d["base_speed"],
                d["acc"], d["eva"], d["armour"], d["dmg"], d["dmg_bonus"],
                d["crit_bonus"], d["species"], d["sight"])
        a.max_hp = d["max_hp"]
        a.energy = d["energy"]
        a.statuses = d["statuses"]
        a.alive = d["alive"]
        a.calm = d["calm"]
        a.flags = d["flags"]
        return a


def apply_status(target, name, turns, stacks=1):
    """Apply a status. Durations refresh to max; poison adds stacks up to cap."""
    cur = target.statuses.get(name)
    if name == POISON:
        t = cur["turns"] if cur else 0
        s = min(POISON_STACK_CAP, (cur["stacks"] if cur else 0) + stacks)
        target.statuses[name] = {"turns": max(t, turns), "stacks": s}
    else:
        target.statuses[name] = {"turns": max(turns, cur["turns"] if cur else 0),
                                 "stacks": 1}


def tick_status(target):
    """Called once per completed action of `target`. Returns log events."""
    events = []
    died = False
    st = target.statuses
    if POISON in st:
        dmg = st[POISON]["stacks"]
        target.hp -= dmg
        events.append(("poison_tick", target, dmg))
        st[POISON]["turns"] -= 1
        if st[POISON]["turns"] <= 0:
            del st[POISON]
            events.append(("status_end", target, POISON))
    if BURNING in st:
        dmg = 2 * st[BURNING].get("stacks", 1)
        target.hp -= dmg
        events.append(("burn_tick", target, dmg))
        st[BURNING]["turns"] -= 1
        if st[BURNING]["turns"] <= 0:
            del st[BURNING]
            events.append(("status_end", target, BURNING))
    for name in list(st.keys()):
        if name in (POISON, BURNING):
            continue
        st[name]["turns"] -= 1
        if st[name]["turns"] <= 0:
            del st[name]
            events.append(("status_end", target, name))
    if target.hp <= 0:
        target.alive = False
        died = True
    return events, died


def clear_movement_blockers(target):
    """Water extinguishes burning."""
    if BURNING in target.statuses:
        del target.statuses[BURNING]


class Level:
    def __init__(self, depth, w, h, tiles, theme):
        self.depth = depth
        self.w = w
        self.h = h
        self.tiles = tiles
        self.theme = theme
        self.rooms = []
        self.up = None
        self.down = None
        self.seen = bytearray(w * h)
        self.items = {}
        self.monsters = []
        self.traps_hidden = set()
        self.traps_found = set()
        self.spawn_timer = 0
        self.spawns_used = 0

    def tile(self, x, y):
        return self.tiles[y * self.w + x]

    def set_tile(self, x, y, code):
        self.tiles[y * self.w + x] = code

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def walkable(self, x, y):
        return self.in_bounds(x, y) and self.tile(x, y) in WALKABLE

    def opaque(self, x, y):
        if not self.in_bounds(x, y):
            return True
        return self.tile(x, y) in OPAQUE

    def monster_at(self, x, y):
        for m in self.monsters:
            if m.alive and m.x == x and m.y == y:
                return m
        return None

    def items_at(self, x, y):
        return self.items.get((x, y), [])

    def to_dict(self):
        return {
            "depth": self.depth, "w": self.w, "h": self.h,
            "tiles": bytes(self.tiles).hex(), "theme": self.theme,
            "rooms": self.rooms, "up": self.up, "down": self.down,
            "seen": bytes(self.seen).hex(),
            "items": {f"{x},{y}": [i.to_dict() for i in v]
                      for (x, y), v in self.items.items()},
            "monsters": [m.to_dict() for m in self.monsters],
            "traps_hidden": sorted(self.traps_hidden),
            "traps_found": sorted(self.traps_found),
            "spawn_timer": self.spawn_timer,
            "spawns_used": self.spawns_used,
        }

    @classmethod
    def from_dict(cls, d, item_from_dict):
        lv = cls(d["depth"], d["w"], d["h"], bytearray(bytes.fromhex(d["tiles"])),
                 d["theme"])
        lv.rooms = d["rooms"]
        lv.up = tuple(d["up"]) if d["up"] else None
        lv.down = tuple(d["down"]) if d["down"] else None
        lv.seen = bytearray(bytes.fromhex(d["seen"]))
        lv.items = {(int(k.split(",")[0]), int(k.split(",")[1])):
                    [item_from_dict(i) for i in v] for k, v in d["items"].items()}
        lv.monsters = [Actor.from_dict(m) for m in d["monsters"]]
        lv.traps_hidden = {tuple(t) for t in d["traps_hidden"]}
        lv.traps_found = {tuple(t) for t in d["traps_found"]}
        lv.spawn_timer = d["spawn_timer"]
        lv.spawns_used = d["spawns_used"]
        return lv


class GameState:
    """Everything that defines a run. Fully serializable; fully deterministic."""

    def __init__(self, seed, rng):
        self.seed = seed
        self.rng = rng
        self.levels = {}
        self.depth = 1
        self.player = None
        self.turn = 0
        self.known_items = {}
        self.appearances = {}
        self.stats = {
            "kills": 0, "damage_dealt": 0, "damage_taken": 0,
            "deepest": 1, "salvage": 0, "potions_quaffed": 0,
            "scrolls_read": 0, "wands_zapped": 0, "won": False,
        }
        self.messages = deque(maxlen=400)
        self._last_msg = None
        self._last_count = 0
        self.memory = {}
        self.tutorial = set()

    def add_message(self, text, kind="neutral"):
        if self.messages and self._last_msg == text:
            self._last_count += 1
            old = self.messages[-1]
            self.messages[-1] = (old[0], old[1], self._last_count)
            return
        self._last_msg = text
        self._last_count = 1
        self.messages.append((text, kind, 1))

    def current_level(self) -> Level:
        return self.levels[self.depth]

    def digest(self):
        payload = {
            "seed": self.seed, "depth": self.depth, "turn": self.turn,
            "known_items": sorted(self.known_items),
            "appearances": self.appearances,
            "stats": self.stats,
            "player": self.player.to_dict(),
            "player_inv": [i.to_dict() for i in getattr(self.player, "inventory", [])],
            "memory": self.memory,
            "tutorial": sorted(self.tutorial),
            "level": self.current_level().to_dict(),
            "levels_meta": {str(k): v.theme for k, v in self.levels.items()},
            "rng": str(self.rng.state()),
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()

    def to_dict(self):
        return {
            "seed": self.seed, "depth": self.depth, "turn": self.turn,
            "known_items": self.known_items, "appearances": self.appearances,
            "stats": self.stats,
            "player": self.player.to_dict(),
            "player_extras": player_extras_to_dict(self.player),
            "memory": self.memory,
            "tutorial": sorted(self.tutorial),
            "levels": {str(k): v.to_dict() for k, v in self.levels.items()},
            "messages": list(self.messages)[-50:],
            "rng_state": encode_rng(self.rng),
        }

    @classmethod
    def from_dict(cls, d, item_from_dict):
        g = cls(d["seed"], RNG(0))
        g.depth = d["depth"]
        g.turn = d["turn"]
        g.known_items = d["known_items"]
        g.appearances = d["appearances"]
        g.stats = d["stats"]
        g.levels = {int(k): Level.from_dict(v, item_from_dict)
                    for k, v in d["levels"].items()}
        g.player = Actor.from_dict(d["player"])
        player_extras_from_dict(g.player, d.get("player_extras", {}))
        g.memory = d.get("memory", {})
        g.tutorial = set(d.get("tutorial", []))
        g.rng = decode_rng(d["rng_state"])
        for m in d.get("messages", []):
            g.messages.append(tuple(m))
        return g


def encode_rng(rng: RNG):
    st = rng.state()
    return {"version": 3, "state": [st[0], list(st[1]), st[2]]}


def decode_rng(d):
    r = RNG(0)
    st = (d["version"], tuple(d["state"][1]), d["state"][2])
    r.set_state(st)
    return r


PLAYER_EXTRAS_KEYS = ("inventory", "equipment", "xp", "level", "xp_pool",
                      "traits", "memory")


def player_extras_to_dict(player):
    out = {}
    for k in PLAYER_EXTRAS_KEYS:
        v = getattr(player, k, None)
        if v is None:
            continue
        if k == "inventory":
            v = [i.to_dict() for i in v]
        elif k == "equipment":
            v = {slot: (i.to_dict() if i else None) for slot, i in v.items()}
        out[k] = v
    return out


def player_extras_from_dict(player, d):
    for k in PLAYER_EXTRAS_KEYS:
        if k not in d:
            continue
        v = d[k]
        if k == "inventory":
            from .items import Item
            v = [Item.from_dict(i) for i in v]
        elif k == "equipment":
            from .items import Item
            v = {slot: (Item.from_dict(i) if i else None)
                 for slot, i in v.items()}
        setattr(player, k, v)
