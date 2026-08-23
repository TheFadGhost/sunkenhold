"""Field of view: symmetric line-based FOV + glow sources + line of sight.

Symmetry guarantee: a FLOOR cell is visible iff the straight line between its
centre and the viewer's centre is unblocked in BOTH directions (bresenham
checked twice), which is symmetric by construction. Walls are drawn when they
touch a visible floor, which keeps cliff faces readable without breaking the
floor-level symmetry contract.
"""
from .engine import OPAQUE

_MULT = None  # retained name for compatibility; no longer used


def compute_fov(level, ox, oy, radius):
    """Return set of visible cells (floors via double-line check,
    opaque neighbours included for readability)."""
    visible = {(ox, oy)}
    r_sq = radius * radius
    w, h = level.w, level.h
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx == 0 and dy == 0:
                continue
            d_sq = dx * dx + dy * dy
            if d_sq > r_sq:
                continue
            x, y = ox + dx, oy + dy
            if not (0 <= x < w and 0 <= y < h):
                continue
            if level.tile(x, y) in OPAQUE:
                continue
            if bresenham_los(level, ox, oy, x, y) and \
                    bresenham_los(level, x, y, ox, oy):
                visible.add((x, y))
    # walls adjacent to visible floor are drawn too
    walls = set()
    for (x, y) in list(visible):
        for j in (-1, 0, 1):
            for i in (-1, 0, 1):
                wx, wy = x + i, y + j
                if 0 <= wx < w and 0 <= wy < h \
                        and level.tile(wx, wy) in OPAQUE:
                    walls.add((wx, wy))
    visible |= walls
    return visible


def bresenham_los(level, x0, y0, x1, y1):
    """True if a straight shot from (x0,y0) to (x1,y1) is unblocked.
    Endpoints themselves may be opaque (actors can stand behind their own tile)."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    x, y = x0, y0
    while (x, y) != (x1, y1):
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
        if (x, y) != (x1, y1) and level.opaque(x, y):
            return False
    return True


def compute_fov_glow(level, ox, oy, radius, glow_tiles, extra=2):
    """Shadowcasting FOV extended by glowing terrain seen out to radius+extra."""
    visible = compute_fov(level, ox, oy, radius)
    far_sq = (radius + extra) ** 2
    for x, y in glow_tiles:
        if (x, y) in visible:
            continue
        dx = x - ox
        dy = y - oy
        if dx * dx + dy * dy > far_sq:
            continue
        if bresenham_los(level, ox, oy, x, y):
            visible.add((x, y))
    return visible
