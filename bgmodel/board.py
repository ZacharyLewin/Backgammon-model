"""
Backgammon board: representation and legal-move generation.

HOW THE BOARD IS STORED
-----------------------
The board is always seen from the side of the player ON ROLL (the same trick
GNU Backgammon uses). Two tuples of 26 numbers, `me` and `opp`:

    index 0        checkers borne off
    index 1..24    points, numbered from THAT player's own side
                   (1 = deepest point of your home board, 24 = furthest back)
    index 25       the bar

Each player moves from high numbers towards 0.
A checker of mine on my point p sits on my opponent's point 25 - p.
After a play we call `swap()` so the other player is on roll.

This means there is only ever one direction of travel to think about,
which keeps the move generator short.
"""
from __future__ import annotations

from dataclasses import dataclass

OFF = 0
BAR = 25
N_CHECKERS = 15

# A move step: (from_point, to_point, die_used, was_hit)
Step = tuple[int, int, int, bool]


def _start_side() -> tuple[int, ...]:
    side = [0] * 26
    side[24] = 2   # back checkers
    side[13] = 5   # mid-point
    side[8] = 3
    side[6] = 5
    return tuple(side)


@dataclass(frozen=True)
class Board:
    me: tuple[int, ...]
    opp: tuple[int, ...]

    # ---------- construction ----------
    @classmethod
    def start(cls) -> "Board":
        return cls(_start_side(), _start_side())

    @classmethod
    def from_points(cls, me: dict[int, int], opp: dict[int, int]) -> "Board":
        """Build a position from {point: count}. Missing checkers are borne off."""
        def side(d: dict[int, int]) -> tuple[int, ...]:
            s = [0] * 26
            for p, n in d.items():
                s[p] = n
            s[OFF] = N_CHECKERS - sum(s[1:])
            return tuple(s)
        return cls(side(me), side(opp))

    def swap(self) -> "Board":
        return Board(self.opp, self.me)

    # ---------- facts about the position ----------
    def pips(self) -> int:
        """Pip count of the player on roll (bar counts 25)."""
        return sum(i * n for i, n in enumerate(self.me))

    def opp_pips(self) -> int:
        return sum(i * n for i, n in enumerate(self.opp))

    def back_checker(self, side: tuple[int, ...]) -> int:
        """Highest point (furthest from home) holding a checker; 0 if none."""
        for i in range(BAR, 0, -1):
            if side[i]:
                return i
        return 0

    def is_race(self) -> bool:
        """True once the two armies have passed each other (no more hitting)."""
        return self.back_checker(self.me) + self.back_checker(self.opp) <= 25

    def is_over(self) -> bool:
        return self.me[OFF] == N_CHECKERS or self.opp[OFF] == N_CHECKERS

    def blots(self) -> int:
        return sum(1 for p in range(1, 25) if self.me[p] == 1)

    def position_id(self) -> str:
        """Compact, readable key: 26 hex digits for me, 26 for opp."""
        return "".join(f"{n:x}" for n in self.me) + "-" + "".join(f"{n:x}" for n in self.opp)

    @classmethod
    def from_position_id(cls, pid: str) -> "Board":
        a, b = pid.split("-")
        return cls(tuple(int(c, 16) for c in a), tuple(int(c, 16) for c in b))

    # ---------- display ----------
    def __str__(self) -> str:
        """Simple text picture. X = player on roll (moving 24 -> 1), O = opponent."""
        def cell(p: int) -> str:
            if self.me[p]:
                return f"X{self.me[p]:<2}"
            q = 25 - p
            if self.opp[q]:
                return f"O{self.opp[q]:<2}"
            return " . "
        top = " ".join(cell(p) for p in range(13, 25))
        bot = " ".join(cell(p) for p in range(12, 0, -1))
        nums_top = " ".join(f"{p:<3}" for p in range(13, 25))
        nums_bot = " ".join(f"{p:<3}" for p in range(12, 0, -1))
        return (
            f"{nums_top}\n{top}\n\n{bot}\n{nums_bot}\n"
            f"X on roll: pips {self.pips()}, bar {self.me[BAR]}, off {self.me[OFF]}  |  "
            f"O: pips {self.opp_pips()}, bar {self.opp[BAR]}, off {self.opp[OFF]}"
        )


# ======================================================================
# Move generation
# ======================================================================

def _can_step(me: list[int], opp: list[int], src: int, die: int) -> bool:
    if me[src] == 0:
        return False
    if me[BAR] and src != BAR:
        return False                      # must enter from the bar first
    dst = src - die
    if dst >= 1:
        return opp[25 - dst] <= 1         # open, or a single opposing blot
    # bearing off: every checker must be home (points 1-6)
    if any(me[i] for i in range(7, 26)):
        return False
    if dst == 0:
        return True                       # exact bear-off
    # overshooting die: only if no checker sits on a higher point
    return not any(me[i] for i in range(src + 1, 7))


def _step(me: list[int], opp: list[int], src: int, die: int) -> tuple[list[int], list[int], Step]:
    me, opp = me.copy(), opp.copy()
    dst = max(src - die, OFF)
    me[src] -= 1
    me[dst] += 1
    hit = False
    if dst >= 1 and opp[25 - dst] == 1:
        opp[25 - dst] = 0
        opp[BAR] += 1
        hit = True
    return me, opp, (src, dst, die, hit)


@dataclass(frozen=True)
class Play:
    steps: tuple[Step, ...]
    after: Board            # resulting position, still from the mover's side

    @property
    def hits(self) -> int:
        return sum(1 for s in self.steps if s[3])

    def notation(self) -> str:
        if not self.steps:
            return "(no play)"
        parts = []
        for src, dst, _die, hit in self.steps:
            a = "bar" if src == BAR else str(src)
            b = "off" if dst == OFF else str(dst)
            parts.append(f"{a}/{b}{'*' if hit else ''}")
        return " ".join(parts)


def _search(me, opp, dice_left, steps, out):
    moved = False
    if dice_left:
        die = dice_left[0]
        sources = [BAR] if me[BAR] else [p for p in range(24, 0, -1) if me[p]]
        for src in sources:
            if _can_step(me, opp, src, die):
                nm, no, st = _step(me, opp, src, die)
                _search(nm, no, dice_left[1:], steps + (st,), out)
                moved = True
    if not moved:
        out.append((steps, me, opp))


def legal_plays(board: Board, dice: tuple[int, int]) -> list[Play]:
    """
    Every distinct legal play for the player on roll.

    Rules enforced:
      * doubles are played four times
      * you must use as many dice as possible
      * if only one die can be played, you must play the larger one if you can
    Plays that reach the same final position are merged (only one kept).
    """
    d1, d2 = dice
    orders = [(d1,) * 4] if d1 == d2 else [(d1, d2), (d2, d1)]

    raw = []
    for order in orders:
        _search(list(board.me), list(board.opp), order, (), raw)

    most = max(len(steps) for steps, _, _ in raw)
    raw = [r for r in raw if len(r[0]) == most]

    if d1 != d2 and most == 1:
        big = max(d1, d2)
        if any(r[0][0][2] == big for r in raw):
            raw = [r for r in raw if r[0][0][2] == big]

    seen: dict[tuple, Play] = {}
    for steps, me, opp in raw:
        key = (tuple(me), tuple(opp))
        if key not in seen:
            seen[key] = Play(steps, Board(tuple(me), tuple(opp)))
    return list(seen.values())


def result_type(winner_side: tuple[int, ...], loser_side: tuple[int, ...]) -> tuple[str, int]:
    """Classify a finished game from the two sides' checker counts."""
    if loser_side[OFF] > 0:
        return "single", 1
    # loser still on the bar or in the winner's home board (loser's points 19-24)
    if loser_side[BAR] or any(loser_side[p] for p in range(19, 25)):
        return "backgammon", 3
    return "gammon", 2
