import unittest

from sunkenhold.game import Game
from sunkenhold.bot import Bot
from sunkenhold.rng import RNG, derive_seed


def scripted_run(seed, moves):
    """Apply an explicit move script; returns list of state digests per turn."""
    g = Game(seed)
    g.new_game()
    digests = [g.state.digest()]
    for (dx, dy) in moves:
        if not g.player.alive or g.victory:
            break
        g.act_move(dx, dy)
        g.run_until_player_input()
        digests.append(g.state.digest())
    return digests


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_script_identical_hashes(self):
        moves = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1)] * 60
        a = scripted_run(1234, moves)
        b = scripted_run(1234, moves)
        self.assertEqual(len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            self.assertEqual(x, y, f"divergence at turn {i}")

    def test_different_seeds_diverge(self):
        moves = [(1, 0), (0, 1), (1, 0), (0, 1)] * 40
        a = scripted_run(1, moves)
        b = scripted_run(2, moves)
        self.assertNotEqual(a[-1], b[-1])

    def test_bot_run_digest_stable(self):
        def once():
            g = Game(555)
            g.new_game()
            b = Bot(g, RNG(derive_seed(555, "bot")))
            hashes = []
            for _ in range(200):
                if not b.step():
                    break
                hashes.append(g.state.digest())
            return hashes
        self.assertEqual(once(), once())


if __name__ == "__main__":
    unittest.main()
