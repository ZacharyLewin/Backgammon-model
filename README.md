# When should you take a double? Testing backgammon's rules of thumb against 5 million simulated games

Strong backgammon players decide whether to double, take or pass in a race using mental
shortcuts — chiefly the **Keith count** and the simpler **8-9-12 rule**. This project builds a
backgammon engine from scratch (Python), stores every simulated game in a database (SQL),
visualises the result (Tableau), and asks a simple question with as much statistical care as
I could manage:

> **When the rule says "take", is the take actually right?**

---

## Findings

600 random doubling-relevant races (roller between 5% behind and 35% ahead in the pip count),
each played out 1,000–6,000 times. Take point = 75% (money game, cubeless).

| | Keith count | 8-9-12 rule |
|---|---|---|
| Right on clearly-decidable positions | **92.1%** | 84.7% |
| … short races (< 60 pips) | 92.8% | 78.7% |
| … medium races (60–89 pips) | 91.1% | 92.4% |
| Wrong after Holm correction (of 600) | **39** | 78 |
| Wrong at a 78% live-cube take point | 30 | 72 |

1. **Keith is the better rule, mostly because of short races.** 8-9-12 matches Keith in medium
   races but falls apart under 60 pips — consistent with what it was designed for, which is a
   useful sign the engine behaves sensibly.
2. **When Keith is wrong, it is almost always too generous.** 35 of its 39 provable errors are
   "take" verdicts in races the roller wins 80–86% of the time — clear passes.
3. **Multiple testing matters.** Testing every position at the 5% level would "discover" 46
   Keith errors. Holm's (1979) step-down correction keeps the family-wise error rate at 5%
   and leaves 39.
4. **The biggest uncertainty wasn't the dice — it was my model.** Every estimate carries a
   tight confidence interval (±1 point at 6,000 trials). But re-running all 600 positions with
   a second, slightly weaker race bot moved win probabilities by **3.4 points on average**, and
   **19 positions flipped from a confident "take" to a confident "pass"** (or back). Statistical
   precision is not accuracy. Only **22 Keith errors survive in both runs** — that is the number
   I'd actually stand behind.

## Method, and why each step is there

| Step | Why |
|---|---|
| Engine written from scratch, 10 rule tests | Results are only as good as the move generator |
| Random race positions filtered to −5%…+35% pip lead | Only study races where doubling is a real question |
| Stage 1: 1,000 games per position | Cheap first estimate |
| Stage 2: top up close calls (CI overlapping 70–83%) to 6,000 | Spend dice where the decision is close |
| Exact one-sided binomial test of each rule's verdict | "Wrong" means the dice reject the rule, not just disagree |
| Holm correction across all 600 tests | 600 tests at 5% would produce ~30 false alarms by luck |
| Sensitivity: 75% and 78% take points | Dead cube vs approximate live-cube take point |
| Head-to-head bot duel (`race_duel.py`) | The stronger race bot (55% vs 45%, ±1.2) plays the main study |
| Full re-run with the other bot, same positions | Measures model error, not just sampling error |

## Honest limits

- **Both bots are imperfect.** A perfect bear-off bot would move the numbers again. The
  conclusions are about relative accuracy of the rules under good-but-not-perfect play.
- **Cubeless playouts.** The 78% line approximates live-cube effects rather than modelling them.
- **Random positions aren't real positions.** Races that arise in actual play are
  distributed differently; the next phase weights by positions from real games.

---

## Run it yourself

Python 3.10+, nothing else required (`pip install pytest` for the tests).

```bash
python3 -m pytest -q                          # 10 tests, each one a rule of backgammon
python3 simulate.py --games 1000              # full games, heuristic v heuristic
python3 race_duel.py --positions 3000         # which race bot is stronger?
python3 keith_study.py --positions 600        # the study (~1 hour on 2 cores)
python3 export_for_tableau.py                 # database -> exports/*.csv
```

The database in `data/backgammon.db` is already filled, so you can go straight to the SQL:

```bash
python3 run_sql.py sql/05_keith_study.sql     # every number in this README
python3 run_sql.py "SELECT * FROM keith_study LIMIT 5"
python3 ask.py "which race lengths does Keith get wrong most?"   # plain English -> SQL (needs an API key)
```

`sql/01` to `sql/05` are a graded SQL course on this data (SELECT → JOINs → window functions →
the study), each ending in an exercise. `ask.py` turns plain-English questions into SQL, shows
the query before running it on a read-only connection, and has a **check mode** that grades
your own attempt.

## How the code fits together

```
bgmodel/board.py       board representation + legal-move generator (start here)
bgmodel/strategies.py  bots: random, heuristic, alt_racer
bgmodel/game.py        plays one full game, records every turn
bgmodel/race.py        race positions, Keith count, rollouts, Wilson intervals
bgmodel/stats.py       exact binomial tests and Holm's procedure, written out by hand
bgmodel/db.py          all database writing
keith_study.py         the study: positions -> adaptive rollouts -> tests -> database
race_duel.py           head-to-head bot comparison
simulate.py            full games -> database
ask.py                 plain-English questions -> SQL
run_sql.py             run a .sql file and print tables
export_for_tableau.py  database -> CSV for Tableau
tests/test_board.py    the rules, written as tests
```

The board is always stored from the side of the player on roll — 26 numbers per side
(0 = borne off, 1–24 = points, 25 = bar), everyone moving downhill — and the sides swap after
each move. That single choice keeps the move generator to about 60 lines.

## Roadmap

1. ✅ Engine, database, race study with multiple-testing control
2. **Exact bear-off database** — remove bot error from short races entirely
3. **Real games** — import my tournament matches; weight the study by positions that actually occur
4. **A learned evaluator** — a self-play neural net (the TD-Gammon idea), with conformal
   prediction intervals so it knows when it doesn't know
