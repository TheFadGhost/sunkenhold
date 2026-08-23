"""Original content: species roster, item catalogues, level themes, artefact.

All names and flavour text are original writing created for Sunkenhold.
"""

FAMILIES = ("beast", "ranged", "undead", "abom", "boss")


class Species:
    def __init__(self, key, letter, name, family, ai, min_depth, weight,
                 hp, speed, acc, eva, armour, dmg, dmg_bonus=0, crit_bonus=0,
                 xp=5, ranged_dmg=None, range_=0, cooldown=0,
                 on_hit_status=None, status_chance=0, sight=7):
        self.key = key
        self.letter = letter
        self.name = name
        self.family = family
        self.ai = ai
        self.min_depth = min_depth
        self.weight = weight
        self.hp = hp
        self.speed = speed
        self.acc = acc
        self.eva = eva
        self.armour = armour
        self.dmg = dmg
        self.dmg_bonus = dmg_bonus
        self.crit_bonus = crit_bonus
        self.xp = xp
        self.ranged_dmg = ranged_dmg
        self.range_ = range_
        self.cooldown = cooldown
        self.on_hit_status = on_hit_status
        self.status_chance = status_chance
        self.sight = sight


SPECIES = {s.key: s for s in [
    Species("gnawling", "g", "gnawling", "beast", "charger", 1, 30,
            5, 110, 0, 2, 0, "1d3", xp=3),
    Species("flittermaw", "f", "flittermaw", "beast", "charger", 1, 14,
            4, 140, 0, 3, 0, "1d2", xp=4),
    Species("seepslime", "s", "seepslime", "abom", "charger", 1, 14,
            10, 66, 0, 0, 1, "1d4", on_hit_status="poison",
            status_chance=15, xp=6),
    Species("husk", "h", "husk", "undead", "charger", 2, 20,
            12, 100, 1, 0, 1, "1d4", xp=8),
    Species("reedshot", "r", "reedshot", "ranged", "kiter", 2, 14,
            7, 100, 1, 1, 0, "1d2", ranged_dmg="1d4", range_=6,
            cooldown=3, xp=10),
    Species("cinder", "c", "cinder sprite", "ranged", "kiter", 3, 10,
            8, 120, 2, 2, 0, "1d2", ranged_dmg="1d3", range_=5,
            cooldown=2, on_hit_status="burning", status_chance=12, xp=12),
    Species("hound", "d", "murk hound", "beast", "pack", 3, 18,
            10, 130, 1, 1, 0, "1d4", xp=9),
    Species("weaver", "w", "tombweaver", "undead", "ambusher", 4, 12,
            14, 100, 2, 1, 1, "1d5", on_hit_status="poison",
            status_chance=10, xp=13),
    Species("poolwatcher", "p", "poolwatcher", "abom", "gaze", 5, 8,
            16, 50, 3, 0, 0, "1d2", ranged_dmg="1d6", range_=4,
            cooldown=2, on_hit_status="stun", status_chance=8, xp=14),
    Species("brute", "b", "barrow brute", "undead", "brute", 8, 5,
            30, 66, 2, 0, 3, "2d5", xp=22),
    Species("skitterking", "k", "skitterking", "beast", "coward", 4, 4,
            18, 120, 2, 3, 0, "1d5", xp=20),
    Species("thrall", "t", "drowned thrall", "undead", "charger", 99, 0,
            10, 100, 1, 0, 0, "1d5", xp=8),
    Species("warden", "W", "Drowned Warden", "boss", "boss", 99, 0,
            60, 90, 3, 2, 2, "2d7", xp=100),
]}

MONSTER_MEMORY_HINTS = {
    "gnawling": "quick, fragile, bites often",
    "flittermaw": "erratic flyer, hard to hit",
    "seepslime": "slow; its touch poisons",
    "husk": "a steady, dull attacker",
    "reedshot": "keeps distance, shoots darts",
    "cinder": "hurls embers that set you alight",
    "hound": "hunts in a pack and circles prey",
    "weaver": "lies still until prey is close",
    "poolwatcher": "does not move; its stare wounds and stuns",
    "brute": "slow, heavily armoured, hits very hard",
    "skitterking": "flees when hurt and comes back with friends",
    "thrall": "the Warden's servant",
    "warden": "guards the Heart; summons thralls",
}


def spawn_table(depth):
    """Weighted (species_key, weight) list available at this depth."""
    if depth == 12:
        return [("thrall", 5), ("weaver", 3), ("brute", 2)]
    out = []
    for s in SPECIES.values():
        if s.weight <= 0 or depth < s.min_depth:
            continue
        fade = max(0.25, 1.0 - max(0, depth - s.min_depth - 4) * 0.15)
        out.append((s.key, s.weight * fade))
    return out


WEAPONS = {
    "worn_dagger": {"name": "worn dagger", "glyph": ")", "dmg": "1d3",
                    "acc_mod": 1, "depth": 1},
    "shortsword": {"name": "short sword", "glyph": ")", "dmg": "1d5",
                   "acc_mod": 0, "depth": 1},
    "spear": {"name": "barbed spear", "glyph": ")", "dmg": "1d5",
              "acc_mod": 1, "depth": 3},
    "mace": {"name": "sunken mace", "glyph": ")", "dmg": "1d6",
             "acc_mod": -1, "depth": 3},
    "longsword": {"name": "longsword", "glyph": ")", "dmg": "1d7",
                  "acc_mod": 0, "depth": 6},
    "waraxe": {"name": "two-handed axe", "glyph": ")", "dmg": "1d8",
               "acc_mod": -1, "depth": 7},
}
RANGED = {
    "shortbow": {"name": "short bow", "glyph": "(", "dmg": "1d5",
                 "acc_mod": 1, "depth": 1},
}
AMMO = {
    "arrows": {"name": "arrows", "glyph": "(", "stack": True, "depth": 1},
}
ARMOURS = {
    "rag_tunic": {"name": "rag tunic", "glyph": "[", "absorb": 1,
                  "eva_mod": 0, "slot": "armour", "depth": 1},
    "leather_cuirass": {"name": "boiled leather", "glyph": "[", "absorb": 2,
                        "eva_mod": 0, "slot": "armour", "depth": 2},
    "scale_hauberk": {"name": "scale hauberk", "glyph": "[", "absorb": 3,
                      "eva_mod": -1, "slot": "armour", "depth": 4},
    "reefplate": {"name": "reefplate harness", "glyph": "[", "absorb": 4,
                  "eva_mod": -1, "slot": "armour", "depth": 7},
    "wooden_shield": {"name": "wooden shield", "glyph": "[", "absorb": 1,
                      "eva_mod": 0, "slot": "shield", "depth": 1},
    "kite_shield": {"name": "kite shield", "glyph": "[", "absorb": 2,
                    "eva_mod": -1, "slot": "shield", "depth": 4},
}
CHARMS = {
    "charm_vigour": {"name": "charm of vigour", "glyph": "=", "effect": "hp5",
                     "desc": "+5 max HP while worn", "depth": 2},
    "charm_eel": {"name": "charm of the eel", "glyph": "=", "effect": "poison_resist",
                  "desc": "poison builds half as fast", "depth": 3},
    "charm_luck": {"name": "knucklebone charm", "glyph": "=", "effect": "crit",
                   "desc": "+10% critical chance", "depth": 4},
    "charm_tide": {"name": "charm of slow tides", "glyph": "=", "effect": "regen",
                   "desc": "recover from wounds twice as fast", "depth": 5},
    "charm_lantern": {"name": "deepwater lantern", "glyph": "=", "effect": "sight",
                      "desc": "+1 sight radius", "depth": 2},
}
POTIONS = {
    "potion_heal": {"name": "healing draught", "effect": "heal",
                    "dice": "2d10", "flat": 6},
    "potion_greater_heal": {"name": "deep remedy", "dice": "4d8", "flat": 8,
                            "effect": "heal"},
    "potion_might": {"name": "bull's blood", "effect": "might", "turns": 40,
                     "amount": 3},
    "potion_swift": {"name": "quickwater", "effect": "haste", "turns": 30},
    "potion_stone": {"name": "stonebrew", "effect": "stone", "turns": 40,
                     "amount": 3},
    "potion_antidote": {"name": "bitterroot tonic", "effect": "cure"},
    "potion_confusion": {"name": "whirlwine", "effect": "confuse", "turns": 10},
    "potion_poison": {"name": "nightjar distillate", "effect": "poison",
                      "turns": 12, "stacks": 3},
}
SCROLLS = {
    "scroll_map": {"name": "chart of the level", "effect": "magic_mapping"},
    "scroll_teleport": {"name": "sidestep verse", "effect": "teleport"},
    "scroll_enchant_weapon": {"name": "whetstone hymn", "effect": "enchant_weapon"},
    "scroll_enchant_armour": {"name": "rivet-song", "effect": "enchant_armour"},
    "scroll_uncurse": {"name": "clean-hands psalm", "effect": "remove_curse"},
    "scroll_fear": {"name": "litany of dread", "effect": "fear"},
}
WANDS = {
    "wand_ember": {"name": "ember wand", "effect": "ember_bolt", "charges": (4, 7)},
    "wand_frost": {"name": "hoarfrost wand", "effect": "frost_bolt",
                   "charges": (4, 7)},
    "wand_tunnel": {"name": "burrowing wand", "effect": "tunnel",
                    "charges": (3, 6)},
}

POTION_APPEARANCES = [
    ("swirling green", "POTION"), ("murky brown", "POTION"),
    ("clear blue", "POTION"), ("cloudy white", "POTION"),
    ("dark red", "POTION"), ("pale gold", "POTION"),
]
SCROLL_TITLES = ["KEXUM", "VORRAI", "TIDLEK", "MARUNO", "SEPHIR", "OLWICK",
                 "BRACKEN", "NIMRET"]
WAND_APPEARANCES = [
    ("knotted walnut wand", "WAND"), ("bone-white wand", "WAND"),
    ("sea-glass wand", "WAND"), ("charred rowan wand", "WAND"),
]

THEMES = {
    "landing": {"name": "the Landing Steps", "hazards": {},
                "monster_mult": 0.5, "item_mult": 1.0},
    "weeping": {"name": "the Weeping Galleries",
                "hazards": {"water": 26}, "monster_mult": 1.0, "item_mult": 1.0},
    "fungal": {"name": "the Fungal Warrens",
               "hazards": {"fungus": 24}, "monster_mult": 1.0, "item_mult": 1.1},
    "collapsed": {"name": "the Collapsed Vaults",
                  "hazards": {"rubble": 34, "traps": 7}, "monster_mult": 1.05,
                  "item_mult": 1.1},
    "boiler": {"name": "the Boiler Deeps",
               "hazards": {"vent": 16, "traps": 5}, "monster_mult": 1.05,
               "item_mult": 1.2},
    "sunken": {"name": "the Sunkenhold itself",
               "hazards": {"water": 12, "fungus": 10, "rubble": 14,
                           "vent": 8, "traps": 6},
               "monster_mult": 1.05, "item_mult": 1.25},
}


def theme_for_depth(depth):
    order = {1: "landing", 2: "weeping", 3: "fungal", 4: "collapsed",
             5: "weeping", 6: "fungal", 7: "collapsed", 8: "weeping",
             9: "fungal", 10: "collapsed", 11: "boiler", 12: "sunken"}
    return order.get(depth, "collapsed")


ARTEFACT_NAME = "the Tideglass Heart"
ARTEFACT_LORE = [
    "A lantern of green glass, beating slowly like a tide that never turns.",
    "The keepers of Sunkenhold drowned their vault rather than surrender it.",
    "It still glows. Whatever waits here never agreed to let it go.",
]

BOSS_TELEGRAPH = "The Drowned Warden gathers black water around its fists."
