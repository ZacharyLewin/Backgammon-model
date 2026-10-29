-- LESSON 4: Testing a human rule of thumb against simulation
-- Run after race_study.py:  python run_sql.py sql/04_race_study.sql

-- Q1. Simulated win probability by pip lead (as % of the roller's count)
SELECT ROUND(lead_pct * 20) * 5          AS lead_pct_band,   -- 5% bands
       COUNT(*)                          AS positions,
       ROUND(AVG(win_prob), 3)           AS avg_win_prob,
       ROUND(AVG(ci_high - ci_low), 3)   AS avg_ci_width
FROM v_race_study
GROUP BY lead_pct_band
ORDER BY lead_pct_band;

-- Q2. How often does the Keith count agree with the simulation on take/pass?
SELECT keith_says_take, sim_says_take, COUNT(*) AS positions
FROM v_race_study
GROUP BY keith_says_take, sim_says_take;

-- Q3. The biggest disagreements: Keith says one thing, the dice say another
SELECT position_id, pips_roller, pips_other, keith_roller, keith_other,
       ROUND(win_prob, 3) AS win_prob, keith_says_take, sim_says_take
FROM v_race_study
WHERE keith_agrees_with_sim = 0
ORDER BY ABS(win_prob - 0.75)
DESC LIMIT 10;

-- TRY: is Keith better in short races (< 60 pips) or long ones?
