"""Morgue: persistent JSONL run records powering high scores and history."""
import json
import os


def append_record(path, record):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    line = json.dumps(record, sort_keys=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_records(path):
    out = []
    if not os.path.exists(path):
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    rec = json.loads(ln)
                    if isinstance(rec, dict):
                        out.append(rec)
                except ValueError:
                    continue
    except OSError:
        return out
    return out


def top_scores(path, n=10):
    recs = [r for r in load_records(path) if isinstance(r.get("score"), int)]
    recs.sort(key=lambda r: (-r["score"], r.get("turns", 0)))
    return recs[:n]
