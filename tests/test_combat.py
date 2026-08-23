import unittest

from sunkenhold.rng import RNG
from sunkenhold.game import Game
from sunkenhold import combat, content as C, items as I
from sunkenhold.items import Item


def fresh(seed=5):
    g = Game(seed)
    g.new_game()
    return g


class TestFormulas(unittest.TestCase):
    def test_hit_chance_clamped_and_stated(self):
        self.assertEqual(combat.hit_chance(0, 0), 75)
        self.assertEqual(combat.hit_chance(10, 0), 95)
        self.assertEqual(combat.hit_chance(-11, 0), 20)
        self.assertEqual(combat.hit_chance(0, 20), 20)

    def test_dice_parse_and_roll_bounds(self):
        lo = min(combat.roll_dice(RNG(1), "2d6") for _ in range(1))
        r = RNG(3)
        rolls = [combat.roll_dice(r, "2d6") for _ in range(300)]
        self.assertTrue(all(2 <= x <= 12 for x in rolls))
        self.assertEqual(len(set(rolls)), 11)

    def test_armour_reduces_min_one(self):
        g = fresh(11)
        m = g.current_level().monsters[0]
        m.armour = 100
        m.hp = 1000
        m.max_hp = 1000
        before = m.hp
        combat.resolve_attack(g, g.player, m)
        self.assertLess(m.hp, before)
        self.assertGreaterEqual(before - m.hp, 1)


class TestPlayerNumbers(unittest.TestCase):
    def test_starting_gear_numbers(self):
        g = fresh(21)
        p = g.player
        w = combat.player_weapon(g)
        self.assertEqual(w["dmg"], "1d5")
        self.assertEqual(w["name"], "short sword")
        absorb = combat.player_absorb(g)
        self.assertEqual(absorb, 1)

    def test_charm_effects_swap_cleanly(self):
        g = fresh(22)
        base = g.player.max_hp
        good = Item("charm_vigour", I.CAT_CHARM)
        g.player.equipment["charm"] = good
        g._apply_charm("charm")
        self.assertEqual(g.player.max_hp, base + 5)
        cursed = Item("charm_vigour", I.CAT_CHARM, cursed=True)
        g.player.equipment["charm"] = cursed
        g._apply_charm("charm")
        self.assertEqual(g.player.max_hp, base - 5)
        g.player.equipment["charm"] = None
        g._apply_charm("charm")
        self.assertEqual(g.player.max_hp, base)


class TestKillRewards(unittest.TestCase):
    def test_kill_grants_xp_and_counts(self):
        g = fresh(31)
        lv = g.current_level()
        m = lv.monsters[0]
        m.flags["asleep"] = False
        xp0 = g.player.xp
        kills0 = g.state.stats["kills"]
        combat.kill(g, m, g.player)
        self.assertEqual(g.state.stats["kills"], kills0 + 1)
        self.assertEqual(g.player.xp,
                         xp0 + C.SPECIES[m.species].xp)


class TestXP(unittest.TestCase):
    def test_thresholds_monotonic(self):
        a = combat.xp_needed(2)
        b = combat.xp_needed(9)
        self.assertLess(a, b)


if __name__ == "__main__":
    unittest.main()
