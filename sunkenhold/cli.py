"""Command line entry: play or simulate."""
import argparse
import os
import sys

from . import __version__, sim


def data_dir():
    d = os.environ.get("SUNKENHOLD_DATA")
    if d:
        return d
    home = os.path.expanduser("~")
    return os.path.join(home, ".sunkenhold")


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="sunkenhold",
        description="Sunkenhold, a terminal roguelike of a drowned keep.")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--wizard", action="store_true",
                    help="debug mode; runs are not recorded in the morgue")
    ap.add_argument("--theme", default=None,
                    choices=["classic", "paper", "contrast", "safe16"])
    ap.add_argument("--mono", action="store_true",
                    help="no colour at all (NO_COLOR is honoured too)")
    ap.add_argument("--unicode", dest="ascii_mode", action="store_false",
                    default=True, help="allow two non-ASCII terrain glyphs")
    ap.add_argument("--version", action="version",
                    version=f"sunkenhold {__version__}")
    sub = ap.add_subparsers(dest="cmd")

    s_sim = sub.add_parser("simulate",
                           help="headless batch run with the greedy bot")
    s_sim.add_argument("--runs", type=int, default=100)
    s_sim.add_argument("--seed0", type=int, default=1)
    s_sim.add_argument("--max-turns", type=int, default=40000)
    s_sim.add_argument("--bot", default="greedy", choices=["greedy", "rush"])
    s_sim.add_argument("--out", default=None)

    args = ap.parse_args(argv)

    if args.cmd == "simulate":
        seeds = list(range(args.seed0, args.seed0 + args.runs))
        results = sim.run_batch(seeds, args.max_turns, args.bot)
        summary = sim.summarize(results)
        for k, v in summary.items():
            print(f"{k}: {v}")
        if args.out:
            sim.write_baselines(args.out, summary, f"{args.seed0}+{args.runs}")
            print(f"baselines written to {args.out}")
        return 0 if not summary["crashes"] else 1

    from .app import App
    from .keys import load_config
    cfg = load_config(data_dir())
    app = App(cfg, data_dir(), seed=args.seed, wizard=args.wizard,
              mono=args.mono or None,
              theme=args.theme or cfg.get("theme"))
    try:
        session = app.title()
        if session is not None:
            app.scr.enter()
            session.loop()
    except Exception:
        import traceback
        app.scr.exit()
        raise
    finally:
        app.scr.exit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
