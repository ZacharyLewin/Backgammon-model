"""
Which race bot is stronger? Play them head to head from random race positions,
each side of every position, so luck of the position cancels out.

    python race_duel.py --positions 1500
"""
import argparse
import random
from multiprocessing import Pool

from bgmodel.board import N_CHECKERS, OFF, legal_plays, result_type
from bgmodel.game import roll
from bgmodel.race import random_race_position, wilson
from bgmodel.strategies import STRATEGIES


def duel(args):
    pid_board, seed = args
    rng = random.Random(seed)
    score = 0
    for first in ("heuristic", "alt_racer"):
        bots = (STRATEGIES[first], STRATEGIES["alt_racer" if first == "heuristic" else "heuristic"])
        board, player = pid_board, 0
        while True:
            play = bots[player].choose(board, legal_plays(board, roll(rng)), rng)
            if play.after.me[OFF] == N_CHECKERS:
                winner = bots[player].name
                break
            board, player = play.after.swap(), 1 - player
        score += winner == "heuristic"
    return score  # 0, 1 or 2 wins for heuristic out of the pair


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--positions", type=int, default=1500)
    args = ap.parse_args()
    rng = random.Random(99)
    tasks = [(random_race_position(rng), rng.randrange(2**31)) for _ in range(args.positions)]
    with Pool(2) as p:
        wins = sum(p.map(duel, tasks, chunksize=20))
    n = 2 * args.positions
    lo, hi = wilson(wins, n)
    print(f"heuristic won {wins}/{n} = {wins/n:.1%}  (95% CI {lo:.1%}-{hi:.1%})")


if __name__ == "__main__":
    main()
