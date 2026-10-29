-- LESSON 2: GROUP BY, CASE, JOIN
-- Run:  python run_sql.py sql/02_aggregates_and_joins.sql

-- Q1. How often does each result happen?
SELECT result, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM games), 1) AS pct
FROM games
GROUP BY result
ORDER BY n DESC;

-- Q2. Win rate by matchup — the JOINs turn strategy ids into names
SELECT w.name AS white, b.name AS black,
       COUNT(*)                                       AS games,
       ROUND(AVG(CASE WHEN g.winner = 0 THEN 1.0 ELSE 0 END), 3) AS white_win_rate,
       ROUND(AVG(CASE WHEN g.winner = 0 THEN g.points ELSE -g.points END), 3) AS white_ppg
FROM games g
JOIN strategies w ON w.strategy_id = g.white_strategy_id
JOIN strategies b ON b.strategy_id = g.black_strategy_id
GROUP BY w.name, b.name;

-- Q3. How many legal plays does each roll give, on average? (doubles are the busy ones)
SELECT die1 || '-' || die2 AS roll,
       ROUND(AVG(n_legal_plays), 1) AS avg_choices,
       MAX(n_legal_plays) AS max_choices
FROM turns
WHERE die1 >= die2
GROUP BY die1, die2
ORDER BY avg_choices DESC
LIMIT 10;

-- Q4. When does contact end? Average turn number at which the race starts
SELECT ROUND(AVG(first_race_turn), 1) AS avg_turn_race_begins
FROM (
    SELECT game_id, MIN(turn_no) AS first_race_turn
    FROM turns
    WHERE is_race = 1
    GROUP BY game_id
);

-- TRY: does the side that hits more often win more often?
--      (hint: SUM(hits) per game and player, then JOIN to games.winner)
