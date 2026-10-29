"""
Simulate full games and store every turn in the database.

    python simulate.py --games 1000 --white heuristic --black random
"""
import argparse
import random
import time
import uuid

from bgmodel import db
from bgmodel.game import play_game
from bgmodel.strategies import STRATEGIES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=1000)
    ap.add_argument("--white", default="heuristic", choices=STRATEGIES)
    ap.add_argument("--black", default="heuristic", choices=STRATEGIES)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    batch = uuid.uuid4().hex[:8]
    con = db.connect()
    t0 = time.time()
    for i in range(args.games):
        g = play_game(STRATEGIES[args.white], STRATEGIES[args.black], rng)
        db.save_game(con, g, batch, args.white, args.black)
        if (i + 1) % 250 == 0:
            con.commit()
            print(f"  {i + 1} games")
    con.commit()
    print(f"Saved {args.games} games ({args.white} v {args.black}) as batch {batch} "
          f"in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
