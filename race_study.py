"""
Phase 1 study: random race positions, rolled out, compared with the Keith count.

    python race_study.py --positions 150 --trials 400
"""
import argparse
import random
import time

from bgmodel import db
from bgmodel.race import keith_verdict, random_race_position, rollout
from bgmodel.strategies import STRATEGIES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--positions", type=int, default=150)
    ap.add_argument("--trials", type=int, default=400, help="games played out per position")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    strat = STRATEGIES["heuristic"]
    con = db.connect()
    sid = db.strategy_id(con, strat.name)
    t0 = time.time()

    for i in range(args.positions):
        b = random_race_position(rng)
        lead = b.opp_pips() - b.pips()
        con.execute(
            """INSERT OR IGNORE INTO race_positions VALUES
               (:pid, :pr, :po, :lead, :pct, :keith_roller, :keith_other,
                :keith_says_double, :keith_says_take)""",
            {"pid": b.position_id(), "pr": b.pips(), "po": b.opp_pips(), "lead": lead,
             "pct": round(lead / b.pips(), 4), **keith_verdict(b)},
        )
        r = rollout(b, strat, args.trials, rng)
        con.execute(
            """INSERT INTO rollouts (position_id, strategy_id, trials, wins, gammons_won,
                                     win_prob, ci_low, ci_high)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (b.position_id(), sid, r["trials"], r["wins"], r["gammons_won"],
             r["win_prob"], r["ci_low"], r["ci_high"]),
        )
        if (i + 1) % 25 == 0:
            con.commit()
            print(f"  {i + 1}/{args.positions} positions  ({time.time() - t0:.0f}s)")
    con.commit()
    print(f"Done: {args.positions} positions x {args.trials} trials in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
