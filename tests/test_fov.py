import unittest

from sunkenhold.mapgen import generate_level
from sunkenhold.rng import RNG
from sunkenhold.engine import Level, T_FLOOR, T_WALL
from sunkenhold.fov import compute_fov, compute_fov_glow, bresenham_los


def empty_room(w=15, h=9):
    tiles = bytearray([T_FLOOR]) * (w * h)
    for x in range(w):
        tiles[x] = T_WALL
        tiles[(h - 1) * w + x] = T_WALL
    for y in range(h):
        tiles[y * w] = T_WALL
        tiles[y * w + w - 1] = T_WALL
    return Level(1, w, h, tiles, "landing")


class TestFOV(unittest.TestCase):
    def test_empty_room_floor_symmetry(self):
        lv = empty_room()
        vis = compute_fov(lv, 7, 4, 8)
        floors = [(x, y) for (x, y) in vis
                  if lv.tile(x, y) == T_FLOOR]
        for (x, y) in floors:
            back = compute_fov(lv, x, y, 8)
            back_floors = [(a, b) for (a, b) in back
                           if lv.tile(a, b) == T_FLOOR]
            self.assertIn((7, 4), back_floors,
                          f"asymmetric floor pair at {(x, y)}")

    def test_wall_blocks(self):
        lv = empty_room()
        # build a wall segment with a gap
        for y in range(1, 5):
            lv.set_tile(7, y, T_WALL)
        vis = compute_fov(lv, 3, 4, 8)
        self.assertNotIn((10, 1), vis)
        self.assertIn((7, 7), vis)  # below the wall via the gap

    def test_symmetry_with_pillars(self):
        lv = empty_room(21, 15)
        for (px, py) in ((5, 5), (14, 9), (10, 3)):
            lv.set_tile(px, py, T_WALL)
        for oy, ox in ((3, 3), (10, 17), (7, 10)):
            vis = compute_fov(lv, ox, oy, 7)
            floors = [(x, y) for (x, y) in vis
                      if lv.tile(x, y) == T_FLOOR][:40]
            for (x, y) in floors:
                back = compute_fov(lv, x, y, 7)
                self.assertIn((ox, oy), back,
                              f"asymmetry ({ox},{oy})->({x},{y})")

    def test_generated_levels_symmetric_sample(self):
        for seed in (1, 2, 3, 4, 5):
            lv, _ = generate_level(3, seed * 7919)
            origins = [(lv.up[0], lv.up[1])]
            count = 0
            for (x, y) in sorted(compute_fov(lv, *origins[0], 7)):
                if lv.tile(x, y) == T_FLOOR and count < 25:
                    back = compute_fov(lv, x, y, 7)
                    self.assertIn(origins[0], back,
                                  f"seed {seed} asymmetry")
                    count += 1

    def test_los_basics(self):
        lv = empty_room()
        lv.set_tile(9, 4, T_WALL)
        self.assertTrue(bresenham_los(lv, 5, 4, 8, 4))
        self.assertFalse(bresenham_los(lv, 5, 4, 10, 4))

    def test_glow_extension(self):
        lv = empty_room()
        glow = [(10, 4)]
        vis = compute_fov_glow(lv, 3, 4, 5, glow)
        self.assertIn((10, 4), vis)


if __name__ == "__main__":
    unittest.main()
