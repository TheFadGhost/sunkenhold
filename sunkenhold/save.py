"""Versioned single-slot save system. Atomic writes; slot deleted on load."""
import hashlib
import json
import os

from . import items as I
from .engine import GameState

SAVE_VERSION = 3


class SaveError(Exception):
    pass


def _digest(payload):
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def save_game(game, path):
    payload = {
        "version": SAVE_VERSION,
        "state": game.state.to_dict(),
        "digest": None,
    }
    payload["digest"] = _digest({"state": payload["state"],
                                 "version": SAVE_VERSION})
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp, path)


def load_state(path):
    """Return the raw state dict after validation. Raises SaveError."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError) as e:
        raise SaveError(f"save file unreadable: {e}") from e
    if not isinstance(payload, dict) or "version" not in payload \
            or "state" not in payload:
        raise SaveError("save file is missing required fields")
    if payload["version"] != SAVE_VERSION:
        raise SaveError(
            f"save was written by version {payload['version']}, this build "
            f"reads version {SAVE_VERSION}")
    want = payload.get("digest")
    if want is None:
        raise SaveError("save has no integrity digest")
    got = _digest({"state": payload["state"], "version": SAVE_VERSION})
    if got != want:
        raise SaveError("save is corrupt (integrity check failed)")
    return payload["state"]


def delete_save(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
