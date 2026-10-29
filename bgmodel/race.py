"""
Phase 1 model: pure races.

Once the armies have passed each other, backgammon becomes a dice race, and
we can estimate the winning chances of any position by simply playing it out
thousands of times (a "rollout"). We then check a famous human rule of thumb,
the Keith count, against those simulated chances.
"""
from __future__ import annotations

import math
import random

from .board import N_CHECKERS, OFF, Board, legal_plays, result_type
from .game import GameRecord, roll
from .strategies import Strategy


def random_race_position(rng: random.Random) -> Board:
    """A random no-contact position with both sides somewhere in the bear-in/bear-off."""
    while True:
        back_me = rng.randint(4, 14)
        back_opp = rng.randint(4, min(14, 25 - back_me))
        me, opp = [0] * 26, [0] * 26
        for side, back in ((me, back_me), (opp, back_opp)):
            n_on_board = rng.randint(8, N_CHECKERS)
            side[back] = 1
            for _ in range(n_on_board - 1):
                side[rng.randint(1, back)] += 1
            side[OFF] = N_CHECKERS - n_on_board
        b = Board(tuple(me), tuple(opp))
        if b.is_race() and not b.is_over() and b.pips() > 20 and b.opp_pips() > 20:
            return b


def keith(side: tuple[int, ...]) -> int:
    """Keith count: pip count plus penalties for wastage."""
    count = sum(i * n for i, n in enumerate(side))
    count += 2 * max(0, side[1] - 1)
    count += 1 * max(0, side[2] - 1)
    count += 1 * max(0, side[3] - 3)
    count += sum(1 for p in (4, 5, 6) if side[p] == 0)
    return count


def keith_verdict(b: Board) -> dict:
    """Roller's count gets +1/7. Double if it exceeds the other's by <= 4; take if by >= 2."""
    roller = keith(b.me) * 8 / 7
    other = keith(b.opp)
    diff = roller - other
    return {
        "keith_roller": round(roller, 2),
        "keith_other": other,
        "keith_says_double": int(diff <= 4),
        "keith_says_take": int(diff >= 2),
    }


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval for a win probability (better than +/- 2 s.e. near 0 or 1)."""
    if n == 0:
        return 0.0, 1.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def rollout(b: Board, strategy: Strategy, trials: int, rng: random.Random) -> dict:
    """Play position b out `trials` times; the side on roll is 'white' and moves first."""
    wins = gammons = 0
    for _ in range(trials):
        g = _play_from(b, strategy, rng)
        if g.winner == 0:
            wins += 1
            gammons += g.points >= 2
    lo, hi = wilson(wins, trials)
    return {"trials": trials, "wins": wins, "gammons_won": gammons,
            "win_prob": wins / trials, "ci_low": lo, "ci_high": hi}


def _play_from(b: Board, strategy: Strategy, rng: random.Random):
    # play_game decides who starts with an opening roll; here the roller is
    # fixed, so we drive the loop directly.
    board, player = b, 0
    while True:
        play = strategy.choose(board, legal_plays(board, roll(rng)), rng)
        after = play.after
        if after.me[OFF] == N_CHECKERS:
            result, points = result_type(after.me, after.opp)
            return GameRecord(player, result, points)
        board, player = after.swap(), 1 - player
