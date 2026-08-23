"""Items: catalogue, per-run appearances, identification, inventory rules."""
from . import content as C

CAT_WEAPON, CAT_RANGED, CAT_AMMO, CAT_ARMOUR, CAT_CHARM = (
    "weapon", "ranged", "ammo", "armour", "charm")
CAT_POTION, CAT_SCROLL, CAT_WAND = "potion", "scroll", "wand"
CAT_SALVAGE, CAT_ARTEFACT = "salvage", "artefact"

STACKABLE = {CAT_POTION, CAT_SCROLL, CAT_AMMO, CAT_SALVAGE}
BACKPACK_CAP = 14

SCROLL_EFFECT_TEXT = {
    "magic_mapping": "reveals the layout of the current floor",
    "teleport": "carries you elsewhere on this floor",
    "enchant_weapon": "permanently improves one wielded weapon",
    "enchant_armour": "permanently improves one worn piece",
    "remove_curse": "breaks curses on everything you carry",
    "fear": "visible enemies flee for a while",
}


class Item:
    __slots__ = ("key", "category", "qty", "enchant", "cursed", "charges",
                 "identified", "appearance", "value")

    def __init__(self, key, category, qty=1, enchant=0, cursed=False,
                 charges=0, identified=False, appearance=0, value=0):
        self.key = key
        self.category = category
        self.qty = qty
        self.enchant = enchant
        self.cursed = cursed
        self.charges = charges
        self.identified = identified
        self.appearance = appearance
        self.value = value

    def to_dict(self):
        return {"key": self.key, "category": self.category, "qty": self.qty,
                "enchant": self.enchant, "cursed": self.cursed,
                "charges": self.charges, "identified": self.identified,
                "appearance": self.appearance, "value": self.value}

    @classmethod
    def from_dict(cls, d):
        return cls(d["key"], d["category"], d["qty"], d["enchant"],
                   d["cursed"], d["charges"], d["identified"],
                   d["appearance"], d["value"])


def _cat_of(key):
    if key in C.WEAPONS:
        return CAT_WEAPON
    if key in C.RANGED:
        return CAT_RANGED
    if key in C.AMMO:
        return CAT_AMMO
    if key in C.ARMOURS:
        return CAT_ARMOUR
    if key in C.CHARMS:
        return CAT_CHARM
    if key in C.POTIONS:
        return CAT_POTION
    if key in C.SCROLLS:
        return CAT_SCROLL
    if key in C.WANDS:
        return CAT_WAND
    raise KeyError(key)


def make_item(rng, depth, category=None):
    """Roll one item appropriate for `depth` using the run RNG."""
    if category is None:
        weights = [
            (CAT_POTION, 30), (CAT_SCROLL, 16), (CAT_WAND, 7),
            (CAT_WEAPON, 9), (CAT_AMMO, 14),
            (CAT_ARMOUR, 11), (CAT_SALVAGE, 18),
        ]
        if any(v["depth"] <= depth for v in C.RANGED.values()):
            weights.append((CAT_RANGED, 3))
        if any(v["depth"] <= depth for v in C.CHARMS.values()):
            weights.append((CAT_CHARM, 4))
        category = rng.weighted(weights)
    if category == CAT_POTION:
        key = rng.choice(list(C.POTIONS))
        it = Item(key, CAT_POTION)
    elif category == CAT_SCROLL:
        key = rng.choice(list(C.SCROLLS))
        it = Item(key, CAT_SCROLL)
    elif category == CAT_WAND:
        key = rng.choice(list(C.WANDS))
        lo, hi = C.WANDS[key]["charges"]
        it = Item(key, CAT_WAND, charges=rng.range(lo, hi))
    elif category == CAT_WEAPON:
        pool = [k for k, v in C.WEAPONS.items() if v["depth"] <= depth]
        key = rng.weighted([(k, 1.0 / max(1, depth - C.WEAPONS[k]["depth"] + 1))
                            for k in pool])
        it = Item(key, CAT_WEAPON)
    elif category == CAT_RANGED:
        it = Item("shortbow", CAT_RANGED)
    elif category == CAT_AMMO:
        it = Item("arrows", CAT_AMMO, qty=rng.range(6, 14))
    elif category == CAT_ARMOUR:
        pool = [k for k, v in C.ARMOURS.items() if v["depth"] <= depth]
        key = rng.weighted([(k, 1.0 / max(1, depth - C.ARMOURS[k]["depth"] + 1))
                            for k in pool])
        it = Item(key, CAT_ARMOUR)
    elif category == CAT_CHARM:
        pool = [k for k, v in C.CHARMS.items() if v["depth"] <= depth]
        key = rng.choice(pool)
        it = Item(key, CAT_CHARM)
    else:
        it = Item("salvage", CAT_SALVAGE, value=rng.range(5, 25))

    if it.category in (CAT_WEAPON, CAT_ARMOUR, CAT_CHARM):
        if rng.chance(12):
            it.cursed = True
            it.enchant = -1
        elif rng.chance(min(35, 8 + depth * 3)):
            it.enchant = 1
        if rng.chance(min(15, depth * 1.5)):
            it.enchant = 2 if it.enchant >= 0 else it.enchant
    return it


def assign_appearances(rng):
    """Per-run mapping from consumable key to appearance index/name."""
    pot = list(C.POTION_APPEARANCES)
    rng.shuffle(pot)
    titles = list(C.SCROLL_TITLES)
    rng.shuffle(titles)
    wands = list(C.WAND_APPEARANCES)
    rng.shuffle(wands)
    app = {}
    for i, k in enumerate(sorted(C.POTIONS)):
        app[k] = pot[i % len(pot)]
    for i, k in enumerate(sorted(C.SCROLLS)):
        app[k] = ("labelled " + titles[i % len(titles)], "SCROLL")
    for i, k in enumerate(sorted(C.WANDS)):
        app[k] = wands[i % len(wands)]
    return app


def game_appearance(game, key, fallback=False):
    if game is not None and key in game.appearances:
        return game.appearances[key]
    if fallback:
        return ("unremarkable", "ITEM_UNID")
    return ("", "ITEM_UNID")


def is_known(game, item):
    if item.category in (CAT_POTION, CAT_SCROLL, CAT_WAND):
        return game.known_items.get(item.key, False)
    return True


def identify_base(game, item):
    first = not game.known_items.get(item.key, False)
    game.known_items[item.key] = True
    return first


def base_name(item):
    if item.category == CAT_WEAPON:
        return C.WEAPONS[item.key]["name"]
    if item.category == CAT_RANGED:
        return C.RANGED[item.key]["name"]
    if item.category == CAT_AMMO:
        return C.AMMO[item.key]["name"]
    if item.category == CAT_ARMOUR:
        return C.ARMOURS[item.key]["name"]
    if item.category == CAT_CHARM:
        return C.CHARMS[item.key]["name"]
    if item.category == CAT_POTION:
        return C.POTIONS[item.key]["name"]
    if item.category == CAT_SCROLL:
        return C.SCROLLS[item.key]["name"]
    if item.category == CAT_WAND:
        return C.WANDS[item.key]["name"]
    if item.category == CAT_SALVAGE:
        return "salvage"
    if item.category == CAT_ARTEFACT:
        from .content import ARTEFACT_NAME
        return ARTEFACT_NAME
    return item.key


def display_name(game, item):
    if item.category in (CAT_POTION, CAT_SCROLL, CAT_WAND) \
            and not is_known(game, item):
        label, _tok = game_appearance(game, item.key)
        cat_word = {CAT_POTION: "potion", CAT_SCROLL: "scroll",
                    CAT_WAND: "wand"}[item.category]
        return f"{cat_word} {label}".replace("potion labelled", "scroll labelled")
    name = base_name(item)
    ench = ""
    if item.enchant:
        ench = f" {'+' if item.enchant > 0 else ''}{item.enchant}"
    cur = "cursed " if item.cursed else ""
    n = f"{cur}{name}{ench}"
    if item.qty > 1:
        n += f" x{item.qty}"
    if item.category == CAT_WAND:
        n += f" ({item.charges})"
    return n


def describe(game, item):
    """Honest mechanical description shown in inventory and look mode."""
    if item.category == CAT_WEAPON:
        w = C.WEAPONS[item.key]
        dmg = f"{w['dmg']}"
        if item.enchant:
            dmg += f"{'+' if item.enchant > 0 else ''}{item.enchant}"
        acc = w["acc_mod"]
        return f"{dmg} dmg, accuracy {acc:+d}, melee"
    if item.category == CAT_RANGED:
        w = C.RANGED[item.key]
        return f"{w['dmg']} dmg, accuracy {w['acc_mod']:+d}, bow (uses arrows)"
    if item.category == CAT_AMMO:
        return "ammunition for bows"
    if item.category == CAT_ARMOUR:
        a = C.ARMOURS[item.key]
        eva = a["eva_mod"]
        extra = f", evasion {eva:+d}" if eva else ""
        return f"absorbs {a['absorb']}, {a['slot']}{extra}"
    if item.category == CAT_CHARM:
        ch = C.CHARMS[item.key]
        if item.cursed:
            return "a cursed trinket; its gift runs backwards"
        return ch["desc"]
    if item.category == CAT_POTION:
        if not is_known(game, item):
            return "effects unverified"
        p = C.POTIONS[item.key]
        e = p["effect"]
        if e == "heal":
            return f"restores {p['dice']}+{p['flat']} HP"
        if e == "might":
            return f"+{p['amount']} damage for {p['turns']} turns"
        if e == "haste":
            return f"move and act half again as fast for {p['turns']} turns"
        if e == "stone":
            return f"+{p['amount']} absorption for {p['turns']} turns"
        if e == "cure":
            return "cures poison and burning"
        if e == "confuse":
            return f"confusion for {p['turns']} turns"
        if e == "poison":
            return f"moderate poison for {p['turns']} turns"
    if item.category == CAT_SCROLL:
        if not is_known(game, item):
            return "script unread"
        return SCROLL_EFFECT_TEXT[C.SCROLLS[item.key]["effect"]]
    if item.category == CAT_WAND:
        if not is_known(game, item):
            return f"{item.charges} charges remaining"
        e = C.WANDS[item.key]["effect"]
        txt = {"ember_bolt": "bolt of flame, 2d6, may ignite",
               "frost_bolt": "bolt of frost, 2d4, slows",
               "tunnel": "melts one wall at range"}[e]
        return f"{txt}; {item.charges} charges left"
    if item.category == CAT_SALVAGE:
        return f"worth {item.value} score"
    if item.category == CAT_ARTEFACT:
        return "the reason you came; carry it to the surface exit"
    return ""


def glyph_for(item):
    if item.category == CAT_WEAPON:
        return ")"
    if item.category in (CAT_RANGED, CAT_AMMO):
        return "("
    if item.category == CAT_ARMOUR:
        return "["
    if item.category == CAT_CHARM:
        return "="
    if item.category == CAT_POTION:
        return "!"
    if item.category == CAT_SCROLL:
        return "?"
    if item.category == CAT_WAND:
        return "/"
    if item.category == CAT_SALVAGE:
        return "*"
    if item.category == CAT_ARTEFACT:
        return "&"
    return "*"


def token_for(game, item):
    from .themes import T
    if item.category in (CAT_POTION, CAT_SCROLL, CAT_WAND) \
            and not is_known(game, item):
        return T.ITEM_UNID
    return {
        CAT_POTION: T.POTION, CAT_SCROLL: T.SCROLL, CAT_WAND: T.WAND,
        CAT_WEAPON: T.WEAPON, CAT_RANGED: T.WEAPON, CAT_AMMO: T.WEAPON,
        CAT_ARMOUR: T.ARMOUR, CAT_CHARM: T.CHARM, CAT_SALVAGE: T.SALVAGE,
        CAT_ARTEFACT: T.ARTEFACT,
    }[item.category]


def add_to_inventory(game, item):
    inv = getattr(game.player, "inventory", None)
    if inv is None:
        game.player.inventory = []
        inv = game.player.inventory
    if item.category in STACKABLE:
        for other in inv:
            if other.key == item.key and other.category == item.category:
                other.qty += item.qty
                return True
    if len(inv) >= BACKPACK_CAP:
        return False
    inv.append(item)
    return True


def total_arrows(game):
    return sum(it.qty for it in getattr(game.player, "inventory", [])
               if it.category == CAT_AMMO)


def consume_arrow(game):
    for it in game.player.inventory:
        if it.category == CAT_AMMO and it.qty > 0:
            it.qty -= 1
            if it.qty <= 0:
                game.player.inventory.remove(it)
            return True
    return False
