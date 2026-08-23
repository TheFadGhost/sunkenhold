"""Seeded RNG contract. Every random draw in Sunkenhold flows through this class."""
import random


class RNG:
    __slots__ = ("_r",)

    def __init__(self, seed):
        self._r = random.Random(seed)

    def random(self) -> float:
        return self._r.random()

    def below(self, n: int) -> int:
        """Uniform int in [0, n)."""
        return self._r.randrange(n)

    def range(self, a: int, b: int) -> int:
        """Uniform int in [a, b]."""
        return self._r.randint(a, b)

    def chance(self, pct: float) -> bool:
        """True with probability pct percent."""
        return self._r.random() * 100.0 < pct

    def choice(self, seq):
        return self._r.choice(seq)

    def shuffle(self, seq):
        self._r.shuffle(seq)

    def weighted(self, pairs):
        """pairs: sequence of (item, weight>0). Returns one item."""
        total = sum(w for _, w in pairs)
        roll = self._r.random() * total
        for item, w in pairs:
            roll -= w
            if roll < 0:
                return item
        return pairs[-1][0]

    def state(self):
        return self._r.getstate()

    def set_state(self, st):
        self._r.setstate(st)


def derive_seed(master_seed: int, salt: str) -> int:
    """Deterministically derive an independent seed from the master seed."""
    r = random.Random(f"{master_seed}|{salt}")
    return r.randrange(1 << 62)
