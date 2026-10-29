-- LESSON 3: Window functions and CTEs (the interview favourites)
-- Run:  python run_sql.py sql/03_window_functions.sql

-- Q1. Pip race through game 1: each player's count, and the change since their last turn
SELECT turn_no, player, pips_mover,
       pips_mover - LAG(pips_mover) OVER (PARTITION BY player ORDER BY turn_no) AS change
FROM turns
WHERE game_id = 1
ORDER BY turn_no
LIMIT 20;

-- Q2. CTE + window: rank games by length within each result type
WITH ranked AS (
    SELECT game_id, result, n_turns,
           RANK() OVER (PARTITION BY result ORDER BY n_turns DESC) AS rnk
    FROM games
)
SELECT * FROM ranked WHERE rnk <= 3 ORDER BY result, rnk;

-- Q3. Win rate by pip lead at the moment the race begins
--     (the first race turn of each game, bucketed into 10-pip bands)
WITH race_start AS (
    SELECT t.game_id, t.player, t.pips_other - t.pips_mover AS lead,
           ROW_NUMBER() OVER (PARTITION BY t.game_id ORDER BY t.turn_no) AS rn
    FROM turns t
    WHERE t.is_race = 1
)
SELECT ((lead + 1000) / 10) * 10 - 1000   -- shift so negatives round down too
                                                                   AS lead_band,
       COUNT(*)                                                   AS games,
       ROUND(AVG(CASE WHEN g.winner = r.player THEN 1.0 ELSE 0 END), 3) AS roller_win_rate
FROM race_start r
JOIN games g USING (game_id)
WHERE rn = 1
GROUP BY lead_band
HAVING COUNT(*) >= 20
ORDER BY lead_band;

-- TRY: a running total of hits for each player across game 1 (SUM(...) OVER ...).
