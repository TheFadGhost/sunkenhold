import unittest

from sunkenhold.engine import Actor, apply_status, tick_status, POISON, \
    BURNING, STUN, SLOW, CONFUSED, NORMAL_COST, move_cost, effective_speed, \
    T_WATER, T_RUBBLE


def mk(status=None, hp=30):
    a = Actor(0, "monster", 0, 0, hp=hp, base_speed=100)
    if status:
        for name, turns, stacks in status:
            apply_status(a, name, turns, stacks)
    return a


class TestStatuses(unittest.TestCase):
    def test_poison_stacks_up_to_cap(self):
        a = mk()
        for _ in range(10):
            apply_status(a, POISON, 6, stacks=2)
        self.assertEqual(a.statuses[POISON]["stacks"], 5)

    def test_duration_refresh_takes_max(self):
        a = mk([(POISON, 3, 1)])
        apply_status(a, POISON, 9, stacks=1)
        self.assertEqual(a.statuses[POISON]["turns"], 9)
        apply_status(a, POISON, 2, stacks=1)
        self.assertEqual(a.statuses[POISON]["turns"], 9)

    def test_poison_ticks_damage_and_expires(self):
        a = mk(status=[(POISON, 2, 3)], hp=5)
        events, died = tick_status(a)
        self.assertEqual(a.hp, 2)
        self.assertFalse(died)
        events, died = tick_status(a)
        self.assertTrue(died)
        self.assertFalse(a.alive)

    def test_burning_tick_then_expire(self):
        a = mk([(BURNING, 1, 1)])
        hp0 = a.hp
        tick_status(a)
        self.assertEqual(hp0 - a.hp, 2)
        tick_status(a)
        self.assertNotIn(BURNING, a.statuses)

    def test_slow_halves_speed(self):
        a = mk([(SLOW, 5, 1)])
        self.assertEqual(effective_speed(a), 50)
        for _ in range(5):
            tick_status(a)
        self.assertEqual(effective_speed(a), 100)

    def test_misc_statuses_expire(self):
        a = mk([(STUN, 1, 1), (CONFUSED, 2, 1)])
        tick_status(a)
        self.assertNotIn(STUN, a.statuses)
        self.assertIn(CONFUSED, a.statuses)
        tick_status(a)
        self.assertNotIn(CONFUSED, a.statuses)


class TestEnergy(unittest.TestCase):
    def test_move_costs_documented(self):
        self.assertEqual(move_cost(1), NORMAL_COST)
        self.assertEqual(move_cost(T_WATER), 200)
        self.assertEqual(move_cost(T_RUBBLE), 150)

    def test_fast_actors_act_more(self):
        fast = Actor(1, "monster", 0, 0, base_speed=150)
        slow = Actor(2, "monster", 0, 0, base_speed=66)
        f_actions = s_actions = 0
        for _ in range(1000):
            fast.energy += effective_speed(fast)
            while fast.energy >= NORMAL_COST:
                fast.energy -= NORMAL_COST
                f_actions += 1
            slow.energy += effective_speed(slow)
            while slow.energy >= NORMAL_COST:
                slow.energy -= NORMAL_COST
                s_actions += 1
        self.assertAlmostEqual(f_actions / s_actions, 150 / 66, delta=0.2)


if __name__ == "__main__":
    unittest.main()
