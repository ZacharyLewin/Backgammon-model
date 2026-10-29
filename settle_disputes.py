"""
Re-roll the positions where the Keith count and the simulation disagree,
with many more trials, to see who was right.

    python settle_disputes.py --trials 10000
"""
import argparse
import random

from bgmodel import db
from bgmodel.board import Board
from bgmodel.race import rollout
from bgmodel.strategies import STRATEGIES


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    strat = STRATEGIES["heuristic"]
    con = db.connect()
    sid = db.strategy_id(con, strat.name)
    disputed = con.execute(
        """SELECT position_id, win_prob, keith_says_take
           FROM v_race_study
           WHERE keith_agrees_with_sim = 0 AND trials < ?""", (args.trials,)).fetchall()

    print(f"{len(disputed)} disputed positions, {args.trials:,} trials each\n")
    for pid, old_p, keith_take in disputed:
        r = rollout(Board.from_position_id(pid), strat, args.trials, rng)
        con.execute(
            """INSERT INTO rollouts (position_id, strategy_id, trials, wins, gammons_won,
                                     win_prob, ci_low, ci_high)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (pid, sid, r["trials"], r["wins"], r["gammons_won"],
             r["win_prob"], r["ci_low"], r["ci_high"]))
        sim_take = r["win_prob"] <= 0.75
        winner = "Keith" if bool(keith_take) == sim_take else "first simulation"
        print(f"  was {old_p:.1%}  now {r['win_prob']:.1%} "
              f"[{r['ci_low']:.1%}-{r['ci_high']:.1%}]  "
              f"Keith says {'take' if keith_take else 'pass'} -> {winner} was right")
    con.commit()


if __name__ == "__main__":
    main()
