"""Semantic colour tokens and the four shipped themes.

Rendering code references tokens only. Every theme maps every token to a
16-colour index plus a 256-colour index; the renderer picks per terminal.
Attributes (dim for remembered, bold for visible entities) are orthogonal to
colour so monochrome play stays fully readable.
"""


class _T:
    pass


T = _T()
_TOKEN_NAMES = [
    "WALL", "FLOOR", "DOOR", "STAIRS", "WATER", "FUNGUS", "RUBBLE", "VENT",
    "TRAP",
    "ITEM_UNID", "POTION", "SCROLL", "WAND", "WEAPON", "ARMOUR", "CHARM",
    "SALVAGE", "ARTEFACT",
    "MON_BEAST", "MON_RANGED", "MON_UNDEAD", "MON_ABOM", "MON_BOSS", "PLAYER",
    "LOG_GOOD", "LOG_BAD", "LOG_NEUTRAL", "LOG_INFO",
    "HP_OK", "HP_LOW", "STATUS_BAD", "STATUS_INFO",
    "UI_BORDER", "UI_DIM", "UI_TITLE",
]
for _n in _TOKEN_NAMES:
    setattr(T, _n, _n)

# (token): (fg16, fg256)
CLASSIC = {
    "WALL": (8, 240), "FLOOR": (8, 238), "DOOR": (6, 37), "STAIRS": (7, 250),
    "WATER": (4, 25), "FUNGUS": (2, 71), "RUBBLE": (8, 243), "VENT": (1, 160),
    "TRAP": (3, 166),
    "ITEM_UNID": (7, 245), "POTION": (5, 170), "SCROLL": (3, 179),
    "WAND": (6, 80), "WEAPON": (7, 252), "ARMOUR": (4, 111),
    "CHARM": (5, 207), "SALVAGE": (3, 220), "ARTEFACT": (2, 85),
    "MON_BEAST": (3, 173), "MON_RANGED": (6, 117), "MON_UNDEAD": (7, 188),
    "MON_ABOM": (5, 176), "MON_BOSS": (5, 199), "PLAYER": (7, 231),
    "LOG_GOOD": (2, 114), "LOG_BAD": (1, 203), "LOG_NEUTRAL": (7, 250),
    "LOG_INFO": (6, 109),
    "HP_OK": (2, 114), "HP_LOW": (1, 203), "STATUS_BAD": (1, 209),
    "STATUS_INFO": (6, 109),
    "UI_BORDER": (8, 240), "UI_DIM": (8, 242), "UI_TITLE": (7, 255),
}

PAPER = {
    "WALL": (0, 238), "FLOOR": (7, 250), "DOOR": (4, 26), "STAIRS": (0, 235),
    "WATER": (4, 33), "FUNGUS": (2, 28), "RUBBLE": (8, 245), "VENT": (1, 124),
    "TRAP": (1, 130),
    "ITEM_UNID": (8, 240), "POTION": (5, 127), "SCROLL": (3, 130),
    "WAND": (6, 30), "WEAPON": (0, 236), "ARMOUR": (4, 21),
    "CHARM": (5, 164), "SALVAGE": (3, 94), "ARTEFACT": (2, 22),
    "MON_BEAST": (1, 88), "MON_RANGED": (6, 24), "MON_UNDEAD": (0, 234),
    "MON_ABOM": (5, 90), "MON_BOSS": (5, 126), "PLAYER": (0, 16),
    "LOG_GOOD": (2, 22), "LOG_BAD": (1, 124), "LOG_NEUTRAL": (0, 236),
    "LOG_INFO": (4, 25),
    "HP_OK": (2, 22), "HP_LOW": (1, 124), "STATUS_BAD": (1, 124),
    "STATUS_INFO": (4, 25),
    "UI_BORDER": (8, 245), "UI_DIM": (8, 245), "UI_TITLE": (0, 232),
}

CONTRAST = {
    "WALL": (7, 15), "FLOOR": (8, 238), "DOOR": (11, 11), "STAIRS": (15, 15),
    "WATER": (12, 21), "FUNGUS": (10, 46), "RUBBLE": (8, 244),
    "VENT": (9, 196), "TRAP": (11, 220),
    "ITEM_UNID": (15, 255), "POTION": (13, 201), "SCROLL": (11, 226),
    "WAND": (14, 51), "WEAPON": (15, 255), "ARMOUR": (12, 39),
    "CHARM": (13, 213), "SALVAGE": (11, 220), "ARTEFACT": (10, 48),
    "MON_BEAST": (9, 208), "MON_RANGED": (14, 87), "MON_UNDEAD": (15, 231),
    "MON_ABOM": (13, 177), "MON_BOSS": (9, 198), "PLAYER": (15, 231),
    "LOG_GOOD": (10, 84), "LOG_BAD": (9, 203), "LOG_NEUTRAL": (15, 255),
    "LOG_INFO": (14, 81),
    "HP_OK": (10, 84), "HP_LOW": (9, 203), "STATUS_BAD": (9, 214),
    "STATUS_INFO": (14, 81),
    "UI_BORDER": (8, 244), "UI_DIM": (8, 246), "UI_TITLE": (15, 231),
}

SAFE16 = {
    "WALL": (8, 8), "FLOOR": (8, 8), "DOOR": (6, 6), "STAIRS": (7, 7),
    "WATER": (4, 4), "FUNGUS": (2, 2), "RUBBLE": (8, 8), "VENT": (1, 1),
    "TRAP": (3, 3),
    "ITEM_UNID": (7, 7), "POTION": (5, 5), "SCROLL": (3, 3),
    "WAND": (6, 6), "WEAPON": (7, 7), "ARMOUR": (4, 4),
    "CHARM": (5, 5), "SALVAGE": (3, 3), "ARTEFACT": (2, 2),
    "MON_BEAST": (1, 1), "MON_RANGED": (6, 6), "MON_UNDEAD": (7, 7),
    "MON_ABOM": (5, 5), "MON_BOSS": (5, 5), "PLAYER": (7, 7),
    "LOG_GOOD": (2, 2), "LOG_BAD": (1, 1), "LOG_NEUTRAL": (7, 7),
    "LOG_INFO": (6, 6),
    "HP_OK": (2, 2), "HP_LOW": (1, 1), "STATUS_BAD": (1, 1),
    "STATUS_INFO": (6, 6),
    "UI_BORDER": (8, 8), "UI_DIM": (8, 8), "UI_TITLE": (7, 7),
}

THEMES = {
    "classic": CLASSIC,
    "paper": PAPER,
    "contrast": CONTRAST,
    "safe16": SAFE16,
}


def get_theme(name):
    return THEMES.get(name, CLASSIC)


def family_token(family):
    return {
        "beast": T.MON_BEAST, "ranged": T.MON_RANGED,
        "undead": T.MON_UNDEAD, "abom": T.MON_ABOM, "boss": T.MON_BOSS,
    }.get(family, T.MON_BEAST)


def species_token(key):
    from . import content as C
    return family_token(C.SPECIES[key].family)


def tile_token(code, found_trap=False):
    if found_trap:
        return T.TRAP
    return {
        0: T.WALL, 1: T.FLOOR, 2: T.DOOR, 3: T.DOOR, 4: T.STAIRS,
        5: T.STAIRS, 6: T.RUBBLE, 7: T.WATER, 8: T.FUNGUS, 9: T.VENT,
    }[code]


def tile_glyph(code, ascii_mode=True):
    g = {0: "#", 1: ".", 2: "+", 3: "'", 4: ">", 5: "<", 6: ",", 7: "~",
         8: '"', 9: "%"}
    if not ascii_mode:
        g = dict(g, **{7: "≈", 8: "❦"})
    return g.get(code, "?")


def monster_glyph(m):
    from . import content as C
    s = C.SPECIES.get(m.species)
    return s.letter if s else "?"
