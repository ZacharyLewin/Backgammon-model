"""
The Keith study: does the Keith count (and the simpler 8-9-12 rule) give the right
take/pass verdict in pure races?

Design
------
1. Draw N random doubling-relevant races (roller between 5% behind and 35% ahead).
2. Stage 1: play each out 1,000 times (cubeless, both sides with the same bot).
3. Stage 2 (adaptive): any position whose 95% interval still overlaps the
   decision zone (70-83%) is topped up to 6,000 trials. Clear positions don't
   need more dice; close ones do.
4. For each rule and each position, an exact one-sided binomial test of the rule's
   verdict, at two take points: 75% (dead cube) and ~78% (live-cube approximation).
5. Holm (1979) correction across all positions, so "the rule is wrong here" is a
   family-wise claim at 5%, not a fishing expedition.
6. Robustness: close positions are re-rolled with a second, weaker race bot.
   If verdicts flip, the result depends on how well the race is played, not
   just on the dice. (race_duel.py shows which bot is stronger: alt_racer
   beats heuristic 55% of the time in races, so alt_racer is the primary.)

    python keith_study.py --positions 600
"""
import argparse
import random
import time
from multiprocessing import Pool

from bgmodel import db
from bgmodel.board import Board
from bgmodel.race import keith, random_race_position, rollout, wilson
from bgmodel.stats import holm, p_value_against_verdict
from bgmodel.strategies import STRATEGIES

THRESHOLDS = {"75": 0.75, "78": 0.78}
ZONE = (0.70, 0.83)
STAGE1, STAGE2, ROBUST = 1_000, 6_000, 3_000

DDL = """
DROP TABLE IF EXISTS keith_study;
CREATE TABLE keith_study (
    position_id TEXT PRIMARY KEY, pips_roller INTEGER, pips_other INTEGER,
    lead_pct REAL, race_length TEXT,
    keith_diff REAL, keith_says_take INTEGER, rule8912_says_take INTEGER,
    trials INTEGER, wins INTEGER, gammons_won INTEGER,
    win_prob REAL, ci_low REAL, ci_high REAL,
    sim_verdict_75 TEXT, sim_verdict_78 TEXT,
    keith_p_75 REAL, keith_holm_p_75 REAL, keith_wrong_75 INTEGER,
    keith_p_78 REAL, keith_holm_p_78 REAL, keith_wrong_78 INTEGER,
    rule8912_p_75 REAL, rule8912_holm_p_75 REAL, rule8912_wrong_75 INTEGER,
    rule8912_p_78 REAL, rule8912_holm_p_78 REAL, rule8912_wrong_78 INTEGER,
    robust_trials INTEGER, robust_win_prob REAL
);
"""


def _work(task):
    pid, trials, seed, strategy = task
    r = rollout(Board.from_position_id(pid), STRATEGIES[strategy], trials, random.Random(seed))
    return pid, r["wins"], r["gammons_won"], trials


def run(tasks, pool, label):
    t0, out = time.time(), []
    for i, res in enumerate(pool.imap_unordered(_work, tasks, chunksize=4), 1):
        out.append(res)
        if i % max(1, len(tasks) // 10) == 0:
            print(f"  {label}: {i}/{len(tasks)}  ({time.time() - t0:.0f}s)", flush=True)
    return out


def verdict(lo, hi, t):
    return "pass" if lo > t else "take" if hi < t else "too close"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--positions", type=int, default=600)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--primary", default="alt_racer", help="bot that plays the rollouts")
    ap.add_argument("--robust", default="heuristic", help="second bot for the robustness check")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    # 1. positions
    boards, seen = [], set()
    while len(boards) < args.positions:
        b = random_race_position(rng)
        lead = (b.opp_pips() - b.pips()) / b.pips()
        if -0.05 <= lead <= 0.35 and b.position_id() not in seen:
            seen.add(b.position_id())
            boards.append(b)
    pids = [b.position_id() for b in boards]

    with Pool(args.workers) as pool:
        # 2. stage 1
        res = {pid: [w, g, n] for pid, w, g, n in
               run([(pid, STAGE1, rng.randrange(2**31), args.primary) for pid in pids], pool, "stage 1")}
        # 3. stage 2: top up close calls
        close = [pid for pid in pids
                 if not (wilson(res[pid][0], res[pid][2])[1] < ZONE[0]
                         or wilson(res[pid][0], res[pid][2])[0] > ZONE[1])]
        print(f"{len(close)} close calls get topped up to {STAGE2:,} trials")
        for pid, w, g, n in run([(pid, STAGE2 - STAGE1, rng.randrange(2**31), args.primary)
                                 for pid in close], pool, "stage 2"):
            res[pid][0] += w; res[pid][1] += g; res[pid][2] += n
        # 6. robustness: close calls re-rolled with a different race bot
        robust = {pid: w / n for pid, w, g, n in
                  run([(pid, ROBUST, rng.randrange(2**31), args.robust) for pid in close],
                      pool, "robustness")}

    # 4-5. tests + Holm
    rows = []
    for b in boards:
        pid = b.position_id()
        wins, gam, n = res[pid]
        lo, hi = wilson(wins, n)
        roller_k, other_k = keith(b.me) * 8 / 7, keith(b.opp)
        lead = (b.opp_pips() - b.pips()) / b.pips()
        rows.append(dict(
            position_id=pid, pips_roller=b.pips(), pips_other=b.opp_pips(),
            lead_pct=round(lead, 4),
            race_length="short (<60)" if b.pips() < 60 else "medium (60-89)" if b.pips() < 90 else "long (90+)",
            keith_diff=round(roller_k - other_k, 2),
            keith_says_take=int(roller_k - other_k >= 2),
            rule8912_says_take=int(lead <= 0.12),
            trials=n, wins=wins, gammons_won=gam, win_prob=wins / n, ci_low=lo, ci_high=hi,
            robust_trials=ROBUST if pid in robust else None, robust_win_prob=robust.get(pid),
        ))
    for tag, t in THRESHOLDS.items():
        for r in rows:
            r[f"sim_verdict_{tag}"] = verdict(r["ci_low"], r["ci_high"], t)
        for rule in ("keith", "rule8912"):
            ps = [p_value_against_verdict(r["wins"], r["trials"], bool(r[f"{rule}_says_take"]), t)
                  for r in rows]
            rejected, adjusted = holm(ps)
            for r, p, rej, adj in zip(rows, ps, rejected, adjusted):
                r[f"{rule}_p_{tag}"], r[f"{rule}_holm_p_{tag}"], r[f"{rule}_wrong_{tag}"] = p, adj, int(rej)

    # save
    con = db.connect()
    con.executescript(DDL)
    sid = db.strategy_id(con, args.primary)
    for b, r in zip(boards, rows):
        con.execute("""INSERT OR IGNORE INTO race_positions VALUES (?,?,?,?,?,?,?,?,?)""",
                    (r["position_id"], r["pips_roller"], r["pips_other"],
                     r["pips_other"] - r["pips_roller"], r["lead_pct"],
                     round(keith(b.me) * 8 / 7, 2), keith(b.opp),
                     int(r["keith_diff"] <= 4), r["keith_says_take"]))
        con.execute("""INSERT INTO rollouts (position_id, strategy_id, trials, wins, gammons_won,
                       win_prob, ci_low, ci_high) VALUES (?,?,?,?,?,?,?,?)""",
                    (r["position_id"], sid, r["trials"], r["wins"], r["gammons_won"],
                     r["win_prob"], r["ci_low"], r["ci_high"]))
    cols = list(rows[0])
    con.executemany(f"INSERT INTO keith_study ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                    [tuple(r[c] for c in cols) for r in rows])
    con.commit()
    games = sum(r["trials"] for r in rows) + ROBUST * len(robust)
    print(f"Done. {len(rows)} positions, {games:,} games played out.")


if __name__ == "__main__":
    main()
