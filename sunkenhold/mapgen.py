"""Procedural level generation with themed variants and guaranteed connectivity."""
from . import content as C
from .engine import (Level, T_WALL, T_FLOOR, T_DOOR_CLOSED, T_DOOR_OPEN,
                     T_DOWN, T_UP, T_RUBBLE, T_WATER, T_FUNGUS, T_VENT)
from .items import make_item, Item, CAT_ARTEFACT
from .rng import RNG

MAP_W, MAP_H = 64, 34


def _carve_room(tiles, w, r):
    for y in range(r[1], r[1] + r[3]):
        for x in range(r[0], r[0] + r[2]):
            tiles[y * w + x] = T_FLOOR


def _overlap(a, b):
    return (a[0] - 1 <= b[0] + b[2] and b[0] - 1 <= a[0] + a[2]
            and a[1] - 1 <= b[1] + b[3] and b[1] - 1 <= a[1] + a[3])


def _corridor(tiles, w, h, a, b, rng):
    """L-shaped corridor between points a and b (order of legs randomized)."""
    x1, y1 = a
    x2, y2 = b
    pts = []
    if rng.chance(50):
        pts += [(x, y1) for x in _span(x1, x2)]
        pts += [(x2, y) for y in _span(y1, y2)]
    else:
        pts += [(x1, y) for y in _span(y1, y2)]
        pts += [(x, y2) for x in _span(x1, x2)]
    for x, y in pts:
        if 0 < x < w - 1 and 0 < y < h - 1:
            if tiles[y * w + x] == T_WALL:
                tiles[y * w + x] = T_FLOOR
    return pts


def _span(a, b):
    if a > b:
        return range(b, a + 1)
    return range(a, b + 1)


def _center(r):
    return (r[0] + r[2] // 2, r[1] + r[3] // 2)


def _place_doors(level):
    w, h = level.w, level.h
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if level.tile(x, y) != T_FLOOR:
                continue
            l, r_ = level.tile(x - 1, y), level.tile(x + 1, y)
            u, d = level.tile(x, y - 1), level.tile(x, y + 1)
            horiz = l == T_WALL and r_ == T_WALL
            vert = u == T_WALL and d == T_WALL
            if horiz != vert:
                neighbours_floor = sum(
                    1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if level.tile(x + dx, y + dy) == T_FLOOR)
                if neighbours_floor >= 2 and _is_doorway(level, x, y):
                    level.set_tile(x, y, T_DOOR_CLOSED)


def _is_doorway(level, x, y):
    """A doorway stands where opening connects room floor to corridor floor."""
    around = [level.tile(x + dx, y + dy)
              for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    return around.count(T_FLOOR) >= 4


def _bfs_dist(level, sx, sy):
    from collections import deque
    dist = {}
    q = deque([(sx, sy)])
    dist[(sx, sy)] = 0
    while q:
        x, y = q.popleft()
        d = dist[(x, y)]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if level.walkable(nx, ny) and (nx, ny) not in dist:
                dist[(nx, ny)] = d + 1
                q.append((nx, ny))
    return dist


def generate_level(depth, seed, artefact=False):
    """Build one level. Deterministic given (depth, seed)."""
    rng = RNG(seed)
    theme_key = C.theme_for_depth(depth)
    theme = C.THEMES[theme_key]
    w, h = MAP_W, MAP_H
    tiles = bytearray([T_WALL]) * (w * h)

    rooms = []
    attempts = 0
    target_rooms = rng.range(7, 10)
    while len(rooms) < target_rooms and attempts < 400:
        attempts += 1
        rw, rh = rng.range(5, 11), rng.range(4, 8)
        rx, ry = rng.range(1, w - rw - 2), rng.range(1, h - rh - 2)
        cand = (rx, ry, rw, rh)
        if not any(_overlap(cand, o) for o in rooms):
            rooms.append(cand)
            _carve_room(tiles, w, cand)

    for i in range(1, len(rooms)):
        a = _center(rooms[i])
        b = _center(rng.choice(rooms[:i]))
        _corridor(tiles, w, h, a, b, rng)
    for _ in range(rng.range(1, 3)):
        a, b = rng.choice(rooms), rng.choice(rooms)
        if a is not b:
            _corridor(tiles, w, h, _center(a), _center(b), rng)

    lv = Level(depth, w, h, tiles, theme_key)
    lv.rooms = rooms
    start_room = rooms[0]
    sx, sy = _center(start_room)
    lv.up = (sx, sy)
    lv.set_tile(sx, sy, T_UP)
    dists = _bfs_dist(lv, sx, sy)
    far = max(dists.items(), key=lambda kv: kv[1])[0]

    if artefact:
        fx, fy = far
        lv.down = None
        lv.set_tile(fx, fy, T_FLOOR)
    else:
        fx, fy = far
        lv.down = (fx, fy)
        lv.set_tile(fx, fy, T_DOWN)

    _apply_hazards(lv, theme, rng)
    _place_doors(lv)
    if lv.tile(*lv.up) == T_DOOR_CLOSED:
        lv.set_tile(*lv.up, T_FLOOR)
    if lv.down and lv.tile(*lv.down) == T_DOOR_CLOSED:
        lv.set_tile(*lv.down, T_FLOOR)
    lv.seen = bytearray(w * h)
    return lv, rng


def _apply_hazards(lv, theme, rng):
    hz = theme["hazards"]
    code_for = {"water": T_WATER, "fungus": T_FUNGUS, "rubble": T_RUBBLE,
                "vent": T_VENT}
    for name, pct in hz.items():
        if name == "traps":
            continue
        code = code_for[name]
        n = int(lv.w * lv.h * pct / 1000)
        for _ in range(n):
            for _try in range(20):
                x, y = rng.below(lv.w - 2) + 1, rng.below(lv.h - 2) + 1
                if lv.tile(x, y) == T_FLOOR:
                    lv.set_tile(x, y, code)
                    break
    trap_n = hz.get("traps", 0) + (min(3, max(0, lv.depth // 4))
                                   if lv.depth > 1 else 0)
    for _ in range(trap_n):
        p = _free_tile(lv, rng, avoid={lv.up})
        if p:
            lv.traps_hidden.add(p)


def free_tiles(level):
    out = []
    for y in range(level.h):
        for x in range(level.w):
            if level.walkable(x, y) and level.tile(x, y) == T_FLOOR:
                out.append((x, y))
    return out


def _free_tile(level, rng, avoid=(), not_near=(), min_d=0):
    for _ in range(200):
        x, y = rng.below(level.w), rng.below(level.h)
        if not level.walkable(x, y) or level.tile(x, y) != T_FLOOR:
            continue
        if (x, y) in avoid:
            continue
        if any(abs(x - ax) + abs(y - ay) < min_d for ax, ay in not_near):
            continue
        return (x, y)
    return None


def populate(level, game_rng, player_pos, alloc_id):
    """Monsters and items for a freshly generated level."""
    theme = C.THEMES[level.theme]
    depth = level.depth
    table = C.spawn_table(depth)
    n_mon = int(round((3 + depth * 1.2) * theme["monster_mult"]))
    if depth == 12:
        n_mon = min(n_mon, 8)
    n_mon = min(n_mon, 18)
    placed = 0
    for _ in range(n_mon):
        pos = _free_tile(level, game_rng, avoid=(level.up,),
                         not_near=[player_pos], min_d=12)
        if pos is None:
            break
        key = game_rng.weighted(table)
        m = make_monster(key, pos[0], pos[1], alloc_id())
        if m:
            level.monsters.append(m)
            placed += 1

    n_items = int(round((3 + game_rng.range(0, 3)) * theme["item_mult"]))
    for _ in range(n_items):
        pos = _free_tile(level, game_rng, avoid=(level.up, level.down),
                         not_near=[player_pos], min_d=6)
        if pos is None:
            continue
        it = make_item(game_rng, depth)
        level.items.setdefault(pos, []).append(it)

    if depth == 12:
        dists = _bfs_dist(level, *player_pos)
        vault = max(dists.items(), key=lambda kv: kv[1])[0]
        warden = make_monster("warden", vault[0], vault[1], alloc_id())
        warden.flags["asleep"] = False
        warden.flags["summon_cd"] = 12
        level.monsters.append(warden)
        for _ in range(2):
            p = _free_tile(level, game_rng, not_near=[vault], min_d=3)
            if p:
                level.monsters.append(
                    make_monster("thrall", p[0], p[1], alloc_id()))
        heart_pos = _free_tile(level, game_rng, avoid=(level.up,),
                               not_near=[vault], min_d=2)
        if heart_pos:
            level.items.setdefault(heart_pos, []).append(
                Item("tideglass", CAT_ARTEFACT))


def make_monster(key, x, y, aid):
    s = C.SPECIES[key]
    from .engine import Actor
    a = Actor(aid, "monster", x, y, s.hp, s.speed, s.acc, s.eva, s.armour,
              s.dmg, s.dmg_bonus, s.crit_bonus, key, s.sight)
    a.flags["ai"] = s.ai
    a.flags["xp"] = s.xp
    a.flags["asleep"] = True
    a.flags["shoot_cd"] = 0
    return a
