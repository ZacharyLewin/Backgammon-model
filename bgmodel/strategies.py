"""
Strategies: given the legal plays, pick one.

These are deliberately simple. They exist so the simulator has something
to play with; the interesting work (a real evaluator, the cube) comes later.
"""
from __future__ import annotations

import random

from .board import BAR, Board, Play

# Number of the 36 rolls that hit a blot at distance d, ignoring blocking points.
# Index = distance. Used to estimate how exposed a blot is.
SHOTS = [0, 11, 12, 14, 15, 15, 17, 6, 6, 5, 3, 2, 3, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1]


class Strategy:
    name = "base"
    description = ""

    def choose(self, board: Board, plays: list[Play], rng: random.Random) -> Play:
        raise NotImplementedError


class RandomStrategy(Strategy):
    name = "random"
    description = "Picks any legal play uniformly at random. The baseline everything should beat."

    def choose(self, board, plays, rng):
        return rng.choice(plays)


def race_score(b: Board) -> float:
    """Race evaluation: fewer pips is better; avoid tall stacks and gaps at home."""
    me = b.me
    stacking = sum(max(0, me[p] - 3) for p in range(1, 7))
    gaps = sum(1 for p in range(1, 7) if me[p] == 0 and any(me[q] for q in range(p + 1, 26)))
    return -b.pips() - 0.5 * stacking - 0.3 * gaps


def blot_risk(b: Board) -> float:
    """Expected pips lost to being hit, roughly: sum over my blots of P(hit) x cost."""
    me, opp = b.me, b.opp
    # positions of opposing checkers in MY numbering (their bar = my 0)
    attackers = {25 - q for q in range(1, 26) if opp[q]}
    risk = 0.0
    for p in range(1, 25):
        if me[p] != 1:
            continue
        shots = sum(SHOTS[p - y] for y in attackers if 0 < p - y < len(SHOTS))
        risk += min(shots, 36) / 36 * (25 - p)
    return risk


def contact_score(b: Board) -> float:
    made_home = sum(1 for p in range(1, 7) if b.me[p] >= 2)
    made_outfield = sum(1 for p in range(7, 10) if b.me[p] >= 2)
    stuck_back = sum(b.me[p] for p in range(19, 26))           # checkers still in their home board
    buried = sum(max(0, b.me[p] - 2) for p in (1, 2))           # checkers wasted deep in my home
    return ((b.opp_pips() - b.pips()) - blot_risk(b) + 3 * made_home + 2 * made_outfield
            - 2 * stuck_back - 2 * buried)


class HeuristicStrategy(Strategy):
    name = "heuristic"
    description = "Hand-tuned scoring: pip balance, blot exposure, made points; tidy bear-in during races."

    def choose(self, board, plays, rng):
        if len(plays) == 1:
            return plays[0]
        if board.is_race():                     # once a race, always a race
            scores = [race_score(p.after) for p in plays]
        else:
            scores = [race_score(p.after) if p.after.is_race() else contact_score(p.after)
                      for p in plays]
        best = max(scores)
        return rng.choice([p for p, s in zip(plays, scores) if s == best])


class AltRacerStrategy(Strategy):
    name = "alt_racer"
    description = ("Race-only control with a different but sensible style: bear off as many as "
                   "possible, then prefer filling gaps over avoiding stacks. Used to check results "
                   "don't hinge on one bot's bear-in habits.")

    def choose(self, board, plays, rng):
        def score(p: Play) -> tuple:
            me = p.after.me
            gaps = sum(1 for q in range(1, 7) if me[q] == 0 and any(me[r] for r in range(q + 1, 26)))
            stacking = sum(max(0, me[q] - 3) for q in range(1, 7))
            return (me[0], -p.after.pips(), -(1.0 * gaps + 0.2 * stacking))
        scores = [score(p) for p in plays]
        best = max(scores)
        return rng.choice([p for p, s in zip(plays, scores) if s == best])


STRATEGIES: dict[str, Strategy] = {
    s.name: s for s in (RandomStrategy(), HeuristicStrategy(), AltRacerStrategy())
}
