"""Player creation, regeneration, charms, level-up choices, monster memory."""
from . import content as C
from .engine import Actor
from .rng import RNG


def make_player(alloc_id):
    p = Actor(alloc_id(), "player", 0, 0, 28, 100, 2, 2, 0, "1d3",
              species=None, sight=7)
    p.inventory = []
    p.equipment = {"weapon": None, "shield": None, "armour": None,
                   "charm": None}
    p.xp = 0
    p.level = 1
    p.flags["regen_threshold"] = 5
    return p


LEVELUP_POOL = [
    ("vitality", 14), ("prowess", 9), ("guard", 8), ("ferocity", 9),
    ("ironblood", 6), ("swiftness", 4), ("farsight", 4),
    ("trait_regen", 3), ("trait_hunter", 3), ("trait_stoic", 2),
]

LEVELUP_TEXT = {
    "vitality": ("Vitality", "+4 max HP and heal 4"),
    "prowess": ("Prowess", "+1 accuracy"),
    "guard": ("Guard", "+1 evasion"),
    "ferocity": ("Ferocity", "+1 damage with every attack"),
    "ironblood": ("Ironblood", "+1 absorption against all damage"),
    "swiftness": ("Swiftness", "+5 speed (act more often)"),
    "farsight": ("Farsight", "+1 sight radius"),
    "trait_regen": ("Tide-toughened", "recover from wounds twice as fast"),
    "trait_hunter": ("Hunter's eye", "+10% critical hit chance"),
    "trait_stoic": ("Stoic blood", "poison lasts half as long on you"),
}


def roll_levelup_choices(rng: RNG):
    pool = list(LEVELUP_POOL)
    picks = []
    while len(picks) < 3 and pool:
        total = sum(w for _, w in pool)
        roll = rng.random() * total
        for i, (name, w) in enumerate(pool):
            roll -= w
            if roll < 0:
                picks.append(name)
                pool.pop(i)
                break
    return picks


def apply_levelup(game, pick):
    p = game.player
    p.flags.setdefault("traits", []).append(pick)
    if pick == "vitality":
        p.max_hp += 4
        p.hp = min(p.max_hp, p.hp + 4)
    elif pick == "prowess":
        p.acc += 1
    elif pick == "guard":
        p.eva += 1
    elif pick == "ferocity":
        p.dmg_bonus += 1
    elif pick == "ironblood":
        p.armour += 1
    elif pick == "swiftness":
        p.base_speed = min(160, p.base_speed + 5)
    elif pick == "farsight":
        p.sight = min(12, p.sight + 1)
    elif pick == "trait_regen":
        p.flags["regen_threshold"] = max(2, p.flags.get("regen_threshold", 8) // 2)
    elif pick == "trait_hunter":
        p.crit_bonus += 10
    elif pick == "trait_stoic":
        p.flags["stoic"] = True


def maybe_regenerate(game):
    """Natural recovery: 1 HP per calm period, paused by recent damage.
    Returns True if healed."""
    p = game.player
    thr = p.flags.get("regen_threshold", 8)
    charm = p.equipment.get("charm")
    if charm and charm.key == "charm_tide" and not charm.cursed:
        thr = max(2, thr // 2)
    if p.calm >= thr and p.hp < p.max_hp:
        p.hp += 1
        p.calm = 0
        return True
    return False


def update_memory(game, species_key, event, value=None):
    mem = getattr(game, "memory", None)
    if mem is None:
        game.memory = {}
        mem = game.memory
    entry = mem.setdefault(species_key, {"seen": 0, "killed": 0})
    if event == "seen":
        entry["seen"] += 1
    elif event == "killed":
        entry["killed"] += 1


def charm_poison_resist(game):
    charm = game.player.equipment.get("charm")
    return bool(charm and charm.key == "charm_eel" and not charm.cursed)


def apply_status_to_player(game, status, turns, stacks=1):
    from .engine import POISON, apply_status
    if status == POISON and charm_poison_resist(game):
        stacks = max(1, stacks // 2)
    if game.player.flags.get("stoic") and status == POISON:
        turns = max(2, turns // 2)
    apply_status(game.player, status, turns, stacks)
