import unittest

from sunkenhold.rng import RNG, derive_seed


class TestRNG(unittest.TestCase):
    def test_deterministic_sequences(self):
        a = RNG(12345)
        b = RNG(12345)
        for _ in range(200):
            self.assertEqual(a.random(), b.random())
            self.assertEqual(a.below(1000), b.below(1000))
            self.assertEqual(a.range(-5, 5), b.range(-5, 5))
            self.assertEqual(a.chance(50), b.chance(50))
            self.assertEqual(a.weighted([("x", 1), ("y", 3)]),
                             b.weighted([("x", 1), ("y", 3)]))

    def test_state_round_trip(self):
        r = RNG(7)
        r.random()
        r.random()
        st = r.state()
        v1 = [r.below(10 ** 6) for _ in range(5)]
        r.set_state(st)
        v2 = [r.below(10 ** 6) for _ in range(5)]
        self.assertEqual(v1, v2)

    def test_derive_seed_stable(self):
        self.assertEqual(derive_seed(42, "floor-3"), derive_seed(42, "floor-3"))
        self.assertNotEqual(derive_seed(42, "floor-3"),
                            derive_seed(42, "floor-4"))

    def test_shuffle_and_choice(self):
        a = RNG(9)
        lst = list(range(20))
        b = RNG(9)
        lst2 = list(range(20))
        a.shuffle(lst)
        b.shuffle(lst2)
        self.assertEqual(lst, lst2)
        self.assertEqual(sorted(lst), list(range(20)))


if __name__ == "__main__":
    unittest.main()
