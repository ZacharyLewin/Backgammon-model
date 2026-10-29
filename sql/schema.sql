-- ================================================================
-- Backgammon model database (SQLite)
-- One row per thing: a strategy, a game, a turn, a race position,
-- a rollout. Tables link to each other through *_id columns.
-- ================================================================

CREATE TABLE IF NOT EXISTS strategies (
    strategy_id   INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    description   TEXT
);

-- One simulated game
CREATE TABLE IF NOT EXISTS games (
    game_id            INTEGER PRIMARY KEY,
    batch_id           TEXT NOT NULL,             -- which run of simulate.py produced it
    white_strategy_id  INTEGER NOT NULL REFERENCES strategies(strategy_id),
    black_strategy_id  INTEGER NOT NULL REFERENCES strategies(strategy_id),
    winner             INTEGER NOT NULL CHECK (winner IN (0, 1)),   -- 0 = white, 1 = black
    result             TEXT NOT NULL CHECK (result IN ('single', 'gammon', 'backgammon')),
    points             INTEGER NOT NULL,
    n_turns            INTEGER NOT NULL,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Every turn of every game, seen from the player about to move
CREATE TABLE IF NOT EXISTS turns (
    game_id        INTEGER NOT NULL REFERENCES games(game_id),
    turn_no        INTEGER NOT NULL,
    player         INTEGER NOT NULL,              -- 0 = white, 1 = black
    die1           INTEGER NOT NULL,
    die2           INTEGER NOT NULL,
    pips_mover     INTEGER NOT NULL,
    pips_other     INTEGER NOT NULL,
    is_race        INTEGER NOT NULL,              -- 1 once there is no more contact
    n_legal_plays  INTEGER NOT NULL,
    play           TEXT NOT NULL,                 -- e.g. '13/7 8/7*'
    hits           INTEGER NOT NULL,
    position_id    TEXT NOT NULL,
    PRIMARY KEY (game_id, turn_no)
);

-- Race positions (no contact) studied by the Monte Carlo rollouts
CREATE TABLE IF NOT EXISTS race_positions (
    position_id        TEXT PRIMARY KEY,
    pips_roller        INTEGER NOT NULL,
    pips_other         INTEGER NOT NULL,
    pip_lead           INTEGER NOT NULL,          -- other - roller (positive = roller ahead)
    lead_pct           REAL NOT NULL,             -- pip_lead / pips_roller
    keith_roller       REAL NOT NULL,             -- Keith-adjusted count, roller (incl. +1/7)
    keith_other        INTEGER NOT NULL,
    keith_says_double  INTEGER NOT NULL,
    keith_says_take    INTEGER NOT NULL
);

-- Results of playing a position out many times
CREATE TABLE IF NOT EXISTS rollouts (
    rollout_id     INTEGER PRIMARY KEY,
    position_id    TEXT NOT NULL REFERENCES race_positions(position_id),
    strategy_id    INTEGER NOT NULL REFERENCES strategies(strategy_id),
    trials         INTEGER NOT NULL,
    wins           INTEGER NOT NULL,
    gammons_won    INTEGER NOT NULL,
    win_prob       REAL NOT NULL,
    ci_low         REAL NOT NULL,                 -- 95% Wilson interval
    ci_high        REAL NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_turns_race ON turns(is_race);
CREATE INDEX IF NOT EXISTS idx_rollouts_pos ON rollouts(position_id);

-- A ready-made view: the race study in one flat table (what Tableau reads).
-- If a position was rolled out more than once, only the biggest rollout is used.
DROP VIEW IF EXISTS v_race_study;
CREATE VIEW v_race_study AS
WITH best AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY position_id
                                 ORDER BY trials DESC, rollout_id DESC) AS rn
    FROM rollouts
)
SELECT
    p.*,
    r.trials, r.wins, r.gammons_won, r.win_prob, r.ci_low, r.ci_high,
    -- money-game cube theory without gammons: take if roller wins <= 75%
    CASE WHEN r.win_prob <= 0.75 THEN 1 ELSE 0 END AS sim_says_take,
    CASE WHEN p.keith_says_take = (r.win_prob <= 0.75) THEN 1 ELSE 0 END AS keith_agrees_with_sim
FROM race_positions p
JOIN best r ON r.position_id = p.position_id AND r.rn = 1;
