"""Headless simulation harness: batch runs, statistics, baselines."""
import json
import os
import statistics
from collections import Counter

from .bot import Bot
from .game import Game


def run_one(seed, max_turns=40000, mode="greedy"):
    g = Game(seed)
    g.new_game()
    from .rng import RNG
    bot = Bot(g, RNG(_bot_seed(seed)), mode=mode)
    turns = 0
    while bot.step():
        if g.state.turn > max_turns:
            return {"seed": seed, "outcome": "softlock",
                    "depth": g.depth, "cause": "turn cap exceeded",
                    "turns": g.state.turn, "score": g.score(),
                    "kills": g.state.stats["kills"], "won": False}
    if g.victory:
        outcome = "win"
    elif g.death_cause:
        outcome = "death"
    else:
        outcome = "abandoned"
    return {"seed": seed, "outcome": outcome,
            "depth": g.depth, "cause": g.death_cause or "escaped",
            "turns": g.state.turn, "score": g.score(),
            "kills": g.state.stats["kills"], "won": bool(g.victory)}


def _bot_seed(master):
    from .rng import derive_seed
    return derive_seed(master, "bot")


def run_batch(seeds, max_turns=40000, mode="greedy", workers=None):
    if len(seeds) >= 4:
        from concurrent.futures import ProcessPoolExecutor
        if workers is None:
            workers = min(8, max(2, os.cpu_count() - 1))
        try:
            with ProcessPoolExecutor(max_workers=workers) as ex:
                results = list(ex.map(_run_one_args,
                                      [(s, max_turns, mode)
                                       for s in seeds]))
            return results
        except Exception as e:
            print(f"parallel run failed ({e!r}); falling back to serial")
    results = []
    for s in seeds:
        try:
            r = run_one(s, max_turns, mode)
            r["crash"] = None
        except Exception as e:
            r = {"seed": s, "outcome": "crash", "error": repr(e),
                 "won": False}
        results.append(r)
    return results


def _run_one_args(args):
    s, mt, mode = args
    try:
        r = run_one(s, mt, mode)
        r["crash"] = None
        return r
    except Exception as e:
        return {"seed": s, "outcome": "crash", "error": repr(e),
                "won": False}


def summarize(results):
    n = len(results)
    wins = sum(1 for r in results if r.get("won"))
    deaths = [r for r in results if r.get("outcome") == "death"]
    crashes = [r for r in results if r.get("outcome") == "crash"]
    softlocks = [r for r in results if r.get("outcome") == "softlock"]
    depths = [r["depth"] for r in results if "depth" in r]
    causes = Counter(r.get("cause") for r in deaths)
    early = sum(1 for r in deaths if r.get("depth", 0) <= 2)
    out = {
        "runs": n, "wins": wins,
        "win_rate": round(wins / max(1, n), 4),
        "median_depth": statistics.median(depths) if depths else 0,
        "mean_depth": round(statistics.mean(depths), 2) if depths else 0,
        "early_deaths_f12": round(early / max(1, len(deaths)), 3),
        "deaths_by_cause": dict(causes.most_common()),
        "crashes": len(crashes), "softlocks": len(softlocks),
        "median_turns": statistics.median(
            [r["turns"] for r in results if "turns" in r]) if depths else 0,
    }
    if crashes:
        out["crash_samples"] = [r.get("error") for r in crashes[:5]]
    return out


def write_baselines(path, summary, seeds_spec):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"seeds": seeds_spec, **summary}, f, indent=1,
                  sort_keys=True)
