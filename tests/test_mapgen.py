import unittest

from sunkenhold.mapgen import generate_level, MAP_W, MAP_H
from sunkenhold.rng import derive_seed
from sunkenhold.engine import T_FLOOR, T_DOWN, T_UP, WALKABLE
from sunkenhold.pathing import dijkstra_map, path_to, step_away

BATCH = 144


class TestGeneration(unittest.TestCase):
    def test_full_batch_connectivity(self):
        """Every generated floor in the batch must connect entrance to
        descent (and contain no orphan walkable tiles)."""
        checked = 0
        for master in range(1, 13):
            for depth in range(1, 13):
                lv, _ = generate_level(depth,
                                       derive_seed(master, f"floor-{depth}"),
                                       artefact=(depth == 12))
                src = lv.up
                dm = dijkstra_map(lv, [src])
                INF = 1 << 30
                if lv.down:
                    di = lv.down[1] * lv.w + lv.down[0]
                    self.assertLess(dm[di], INF,
                                    f"master {master} depth {depth}: "
                                    "descent unreachable")
                orphans = sum(
                    1 for i in range(lv.w * lv.h)
                    if lv.tiles[i] in WALKABLE and dm[i] >= INF)
                self.assertEqual(
                    orphans, 0,
                    f"master {master} depth {depth}: {orphans} orphan tiles")
                checked += 1
        self.assertEqual(checked, BATCH)

    def test_artefact_floor_has_heart_and_no_down(self):
        from sunkenhold.game import Game
        g = Game(505)
        g.ensure_level(12)
        g.state.depth = 12
        lv = g.current_level()
        self.assertIsNone(lv.down)
        hearts = [it for items in lv.items.values() for it in items
                  if it.category == "artefact"]
        self.assertEqual(len(hearts), 1)
        wardens = [m for m in lv.monsters if m.species == "warden"]
        self.assertEqual(len(wardens), 1)

    def test_stairs_on_distinct_rooms_and_tiles(self):
        lv, _ = generate_level(2, derive_seed(3, "floor-2"))
        self.assertNotEqual(lv.up, lv.down)
        self.assertEqual(lv.tile(*lv.up), T_UP)
        self.assertEqual(lv.tile(*lv.down), T_DOWN)
        d = dijkstra_map(lv, [lv.up])[lv.down[1] * lv.w + lv.down[0]]
        self.assertGreater(d, 0)

    def test_deterministic_generation(self):
        a, _ = generate_level(4, 999)
        b, _ = generate_level(4, 999)
        self.assertEqual(bytes(a.tiles), bytes(b.tiles))
        self.assertEqual([m.pos for m in a.monsters],
                         [m.pos for m in b.monsters])


class TestPathing(unittest.TestCase):
    def test_unreachable_goal_returns_empty(self):
        lv, _ = generate_level(1, derive_seed(11, "floor-1"))
        # find a wall cell fully enclosed by walls: use map corner interior
        goal = (0, 0)
        steps = path_to(lv, lv.up, goal)
        self.assertEqual(steps, [])

    def test_path_steps_are_adjacent_and_walkable(self):
        lv, _ = generate_level(3, derive_seed(21, "floor-3"))
        steps = path_to(lv, lv.up, lv.down)
        cur = lv.up
        for s in steps:
            self.assertTrue(lv.walkable(*s))
            self.assertLessEqual(max(abs(s[0] - cur[0]), abs(s[1] - cur[1])),
                                 1)
            cur = s
        self.assertEqual(cur, lv.down)

    def test_step_away_bounded(self):
        lv, _ = generate_level(2, derive_seed(31, "floor-2"))
        dm = dijkstra_map(lv, [lv.up])
        x, y = lv.up
        for _ in range(200):
            nxt = step_away(lv, x, y, dm)
            if nxt is None:
                break
            x, y = nxt


if __name__ == "__main__":
    unittest.main()
