import json
import os
import tempfile
import unittest

from sunkenhold.game import Game
from sunkenhold.bot import Bot
from sunkenhold.rng import RNG, derive_seed
from sunkenhold import save as SAVE


def play(g, turns=120):
    b = Bot(g, RNG(derive_seed(g.seed, "bot")))
    n = 0
    while b.step() and g.state.turn < turns:
        n += 1
    return b


class TestSaveRoundTrip(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="sh_save_")
        self.path = os.path.join(self.dir, "run.save")

    def test_round_trip_identical_digest(self):
        g = Game(77)
        g.new_game()
        play(g, 150)
        want = g.state.digest()
        SAVE.save_game(g, self.path)
        st = SAVE.load_state(self.path)
        g2 = Game.from_state(st)
        self.assertEqual(want, g2.state.digest())

    def test_version_mismatch_rejected(self):
        g = Game(78)
        g.new_game()
        SAVE.save_game(g, self.path)
        with open(self.path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        payload["version"] = SAVE.SAVE_VERSION + 99
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        with self.assertRaises(SAVE.SaveError):
            SAVE.load_state(self.path)

    def test_tampered_state_rejected(self):
        g = Game(79)
        g.new_game()
        SAVE.save_game(g, self.path)
        with open(self.path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        payload["state"]["turn"] = 999999
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        with self.assertRaises(SAVE.SaveError):
            SAVE.load_state(self.path)

    def test_garbage_file_rejected(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{not json at all")
        with self.assertRaises(SAVE.SaveError):
            SAVE.load_state(self.path)

    def test_delete_idempotent(self):
        SAVE.delete_save(self.path)
        SAVE.delete_save(self.path)


if __name__ == "__main__":
    unittest.main()
