"""
Playing a full game between two strategies, and recording every turn.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .board import Board, legal_plays, result_type
from .strategies import Strategy

WHITE, BLACK = 0, 1


@dataclass
class TurnRecord:
    turn_no: int
    player: int
    die1: int
    die2: int
    pips_mover: int
    pips_other: int
    is_race: bool
    n_legal_plays: int
    play: str
    hits: int
    position_id: str


@dataclass
class GameRecord:
    winner: int
    result: str          # single / gammon / backgammon
    points: int
    turns: list[TurnRecord] = field(default_factory=list)


def roll(rng: random.Random) -> tuple[int, int]:
    return rng.randint(1, 6), rng.randint(1, 6)


def play_game(white: Strategy, black: Strategy, rng: random.Random,
              start: Board | None = None, max_turns: int = 2000) -> GameRecord:
    strategies = (white, black)
    board = start or Board.start()

    # Opening: each side rolls one die; higher die moves first using both.
    while True:
        a, b = roll(rng)
        if a != b:
            break
    player = WHITE if a > b else BLACK
    dice = (a, b)

    turns: list[TurnRecord] = []
    for turn_no in range(1, max_turns + 1):
        plays = legal_plays(board, dice)
        choice = strategies[player].choose(board, plays, rng)
        turns.append(TurnRecord(
            turn_no=turn_no, player=player, die1=dice[0], die2=dice[1],
            pips_mover=board.pips(), pips_other=board.opp_pips(),
            is_race=board.is_race(), n_legal_plays=len(plays),
            play=choice.notation(), hits=choice.hits,
            position_id=board.position_id(),
        ))
        after = choice.after
        if after.me[0] == 15:
            result, points = result_type(after.me, after.opp)
            return GameRecord(player, result, points, turns)
        board = after.swap()
        player = 1 - player
        dice = roll(rng)
    raise RuntimeError("game did not finish")
