"""
Everything that talks to the SQLite database lives here.

SQLite is a whole database in one file (data/backgammon.db). Python ships
with the `sqlite3` module, so there is nothing to install.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from .game import GameRecord
from .strategies import STRATEGIES

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("BGMODEL_DB", ROOT / "data" / "backgammon.db"))
SCHEMA = ROOT / "sql" / "schema.sql"


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    # make sure every strategy has a row
    con.executemany(
        "INSERT OR IGNORE INTO strategies (name, description) VALUES (?, ?)",
        [(s.name, s.description) for s in STRATEGIES.values()],
    )
    con.commit()
    return con


def strategy_id(con: sqlite3.Connection, name: str) -> int:
    return con.execute("SELECT strategy_id FROM strategies WHERE name = ?", (name,)).fetchone()[0]


def save_game(con: sqlite3.Connection, g: GameRecord, batch_id: str, white: str, black: str) -> int:
    cur = con.execute(
        """INSERT INTO games (batch_id, white_strategy_id, black_strategy_id,
                              winner, result, points, n_turns)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (batch_id, strategy_id(con, white), strategy_id(con, black),
         g.winner, g.result, g.points, len(g.turns)),
    )
    game_id = cur.lastrowid
    con.executemany(
        """INSERT INTO turns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(game_id, t.turn_no, t.player, t.die1, t.die2, t.pips_mover, t.pips_other,
          int(t.is_race), t.n_legal_plays, t.play, t.hits, t.position_id) for t in g.turns],
    )
    return game_id
