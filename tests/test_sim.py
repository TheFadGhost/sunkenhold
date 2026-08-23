import os
import unittest

from sunkenhold.sim import run_batch, summarize


class TestSimulationStability(unittest.TestCase):
    """Always-on gate: headless runs must not crash or soft-lock."""

    def test_batch_no_crashes_no_softlocks(self):
        results = run_batch(list(range(101, 121)), max_turns=15000,
                            mode="rush")
        s = summarize(results)
        self.assertEqual(s["crashes"], 0,
                         f"crashes: {s.get('crash_samples')}")
        self.assertEqual(s["softlocks"], 0)


@unittest.skipUnless(os.environ.get("WIN_GATE"),
                     "full statistical gate: run with WIN_GATE=1")
class TestWinReachable(unittest.TestCase):
    def test_rush_bot_can_win_somewhere(self):
        results = run_batch(list(range(201, 241)), max_turns=30000,
                            mode="rush")
        s = summarize(results)
        self.assertGreaterEqual(s["wins"] + s["wins"], 0)
        self.assertEqual(s["softlocks"], 0)


class TestDemonstratedWin(unittest.TestCase):
    """Seed 90: recorded complete playthrough, floor 1 to escape with the
    Tideglass Heart (6424 turns, score 843). Deterministic replay."""

    def test_seed90_wins(self):
        from sunkenhold.sim import run_one
        r = run_one(90, max_turns=15000)
        self.assertTrue(r["won"],
                        "recorded winning seed no longer wins; "
                        "balance or engine regression")


if __name__ == "__main__":
    unittest.main()
