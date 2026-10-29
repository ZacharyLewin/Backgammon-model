-- LESSON 5: The Keith study — the numbers behind the write-up
-- Run after keith_study.py:  python3 run_sql.py sql/05_keith_study.sql

-- Q1. The headline: how often does each rule match the dice? (75% take point)
SELECT COUNT(*)                                                         AS positions,
       SUM(sim_verdict_75 = 'too close')                                AS too_close_to_call,
       ROUND(AVG(CASE WHEN sim_verdict_75 != 'too close'
                      THEN (sim_verdict_75 = 'take') = keith_says_take END), 3)    AS keith_accuracy,
       ROUND(AVG(CASE WHEN sim_verdict_75 != 'too close'
                      THEN (sim_verdict_75 = 'take') = rule8912_says_take END), 3) AS rule8912_accuracy
FROM keith_study;

-- Q2. Where the rules are demonstrably wrong — survives a Holm correction across every position
SELECT SUM(keith_wrong_75)    AS keith_wrong_75,
       SUM(rule8912_wrong_75) AS rule8912_wrong_75,
       SUM(keith_wrong_78)    AS keith_wrong_78,
       SUM(rule8912_wrong_78) AS rule8912_wrong_78
FROM keith_study;

-- Q3. Same question WITHOUT Holm: how many 'discoveries' would a careless analyst report?
SELECT SUM(keith_p_75 < 0.05)    AS keith_naive_75,
       SUM(rule8912_p_75 < 0.05) AS rule8912_naive_75
FROM keith_study;

-- Q4. Does accuracy depend on race length?
SELECT race_length,
       COUNT(*) AS positions,
       ROUND(AVG(CASE WHEN sim_verdict_75 != 'too close'
                      THEN (sim_verdict_75 = 'take') = keith_says_take END), 3)    AS keith_accuracy,
       ROUND(AVG(CASE WHEN sim_verdict_75 != 'too close'
                      THEN (sim_verdict_75 = 'take') = rule8912_says_take END), 3) AS rule8912_accuracy
FROM keith_study
GROUP BY race_length
ORDER BY MIN(pips_roller);

-- Q5. Robustness: on close calls, how much does a different (sensible) race bot move the answer?
SELECT COUNT(*)                                         AS close_calls_rerolled,
       ROUND(AVG(ABS(robust_win_prob - win_prob)), 3)   AS avg_shift,
       ROUND(MAX(ABS(robust_win_prob - win_prob)), 3)   AS max_shift,
       SUM((robust_win_prob <= 0.75) != (win_prob <= 0.75)) AS verdict_flips
FROM keith_study
WHERE robust_win_prob IS NOT NULL;

-- Q6. The positions where Keith is provably wrong, worst first
SELECT pips_roller, pips_other, ROUND(lead_pct * 100, 1) AS lead_pct,
       keith_diff, CASE keith_says_take WHEN 1 THEN 'take' ELSE 'pass' END AS keith_says,
       ROUND(win_prob, 3) AS win_prob, ROUND(ci_low, 3) AS ci_low, ROUND(ci_high, 3) AS ci_high,
       trials, ROUND(keith_holm_p_75, 5) AS holm_p
FROM keith_study
WHERE keith_wrong_75 = 1
ORDER BY keith_holm_p_75
LIMIT 15;

-- TRY: which way does Keith err when it's wrong — too willing to take, or too quick to pass?
