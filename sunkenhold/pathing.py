"""Shared pathfinding. One Dijkstra map per player position serves all actors."""
import heapq

from .engine import move_cost

_WALK = {1, 2, 3, 4, 5, 6, 7, 8, 9}
_COST = {1: 100, 2: 200, 3: 100, 4: 100, 5: 100, 6: 150, 7: 200, 8: 100,
         9: 100}


def dijkstra_map(level, sources):
    """Cost-to-reach map over walkable tiles, returned as a flat list indexed
    by y*w+x (1<<30 for unreachable). Terrain energy costs are respected."""
    w, h = level.w, level.h
    tiles = level.tiles
    INF = 1 << 30
    dist = [INF] * (w * h)
    pq = []
    for sx, sy in sources:
        i = sy * w + sx
        if 0 <= sx < w and 0 <= sy < h and tiles[i] in _WALK:
            dist[i] = 0
            pq.append((0, i))
    heapq.heapify(pq)
    push = heapq.heappush
    pop = heapq.heappop
    while pq:
        d, i = pop(pq)
        if d > dist[i]:
            continue
        x = i % w
        nd_list = []
        if x > 0:
            nd_list.append(i - 1)
        if x < w - 1:
            nd_list.append(i + 1)
        if i >= w:
            nd_list.append(i - w)
        if i + w < w * h:
            nd_list.append(i + w)
        for j in nd_list:
            c = tiles[j]
            if c not in _WALK:
                continue
            nd = d + _COST[c]
            if nd < dist[j]:
                dist[j] = nd
                push(pq, (nd, j))
    return dist


def get_dist(dmap, level, x, y):
    return dmap[y * level.w + x]


_NEIGH8 = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))


def _at(level, dmap, x, y):
    if 0 <= x < level.w and 0 <= y < level.h:
        v = dmap[y * level.w + x]
        if v < (1 << 30):
            return v
    return None


def step_toward(level, x, y, dmap, occupied=None):
    """Next step descending the shared influence map. None if no route."""
    best = None
    best_val = _at(level, dmap, x, y)
    if best_val is None:
        best_val = 1 << 30
    for dx, dy in _NEIGH8:
        nx, ny = x + dx, y + dy
        if occupied and (nx, ny) in occupied:
            continue
        v = _at(level, dmap, nx, ny)
        if v is not None and v < best_val:
            best_val = v
            best = (nx, ny)
    return best


def step_away(level, x, y, dmap, occupied=None):
    """Next step ascending the influence map (fleeing)."""
    best = None
    best_val = _at(level, dmap, x, y)
    if best_val is None:
        best_val = -(1 << 30)
    for dx, dy in _NEIGH8:
        nx, ny = x + dx, y + dy
        if not level.walkable(nx, ny) or (occupied and (nx, ny) in occupied):
            continue
        v = dmap[ny * level.w + nx]
        if v > (1 << 29):
            continue
        if v > best_val:
            best_val = v
            best = (nx, ny)
    return best


def flank_target(level, monster, player, dmap, occupied):
    """Pack hunters aim for a free tile adjacent to the prey, spread out."""
    cands = []
    px, py = player.x, player.y
    mxv, myv = monster.x, monster.y
    for dx, dy in _NEIGH8:
        nx, ny = px + dx, py + dy
        if (nx, ny) == (mxv, myv):
            return (nx, ny)
        if not level.walkable(nx, ny) or (nx, ny) in occupied:
            continue
        d_here = _at(level, dmap, nx, ny)
        if d_here is None:
            continue
        cands.append(((nx, ny),
                      d_here * 4 + abs(nx - mxv) + abs(ny - myv)))
    if not cands:
        return None
    cands.sort(key=lambda kv: (kv[1], kv[0]))
    return cands[0][0]


def path_to(level, start, goal):
    """Dijkstra shortest path start->goal as a list of steps (excluding start).
    Returns [] when unreachable."""
    if start == goal or not level.walkable(*goal):
        return []
    dmap = dijkstra_map(level, [tuple(goal)])
    si = start[1] * level.w + start[0]
    if si >= len(dmap) or dmap[si] >= (1 << 30):
        return []
    path = []
    cur = tuple(start)
    guard = level.w * level.h + 8
    while cur != tuple(goal) and guard > 0:
        guard -= 1
        nxt = step_toward(level, cur[0], cur[1], dmap)
        if nxt is None:
            return []
        path.append(nxt)
        cur = nxt
    return path if cur == tuple(goal) else []


def nearest_unexplored(level, seen, start):
    """Closest unseen walkable tile by path distance, or None."""
    dmap = dijkstra_map(level, [start])
    best, best_d = None, 1 << 60
    w = level.w
    for idx in range(len(dmap)):
        d = dmap[idx]
        if d < best_d and d < (1 << 30) and not seen[idx]:
            best_d = d
            best = (idx % w, idx // w)
    return best
