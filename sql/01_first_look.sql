-- LESSON 1: SELECT, WHERE, ORDER BY, LIMIT
-- Run:  python run_sql.py sql/01_first_look.sql

-- Q1. How many games and turns are stored?
SELECT
    (SELECT COUNT(*) FROM games) AS games,
    (SELECT COUNT(*) FROM turns) AS turns;

-- Q2. Look at the first few turns of game 1
SELECT turn_no, player, die1, die2, pips_mover, pips_other, play
FROM turns
WHERE game_id = 1
ORDER BY turn_no
LIMIT 10;

-- Q3. The longest games ever played
SELECT game_id, n_turns, result, points
FROM games
ORDER BY n_turns DESC
LIMIT 5;

-- Q4. Every turn where a double 6 was rolled from the bar (look for 'bar/' in the play)
SELECT game_id, turn_no, play
FROM turns
WHERE die1 = 6 AND die2 = 6 AND play LIKE 'bar/%'
LIMIT 10;

-- TRY: find turns where the player had no legal play at all (play = '(no play)').
