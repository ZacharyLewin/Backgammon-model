"""
Run every query in a .sql file and print the results as tables.

    python run_sql.py sql/01_first_look.sql
    python run_sql.py "SELECT COUNT(*) FROM games"
"""
import sqlite3
import sys
from pathlib import Path

from bgmodel import db


def statements(text: str):
    buf = ""
    for line in text.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            if buf.strip():
                yield buf.strip()
            buf = ""


def show(cur: sqlite3.Cursor, limit: int = 25):
    if cur.description is None:
        return
    cols = [c[0] for c in cur.description]
    rows = cur.fetchmany(limit)
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)
    table = [cols] + [[fmt(v) for v in r] for r in rows]
    widths = [max(len(r[i]) for r in table) for i in range(len(cols))]
    for j, r in enumerate(table):
        print("  ".join(v.ljust(w) for v, w in zip(r, widths)))
        if j == 0:
            print("  ".join("-" * w for w in widths))
    print()


def main():
    arg = sys.argv[1]
    text = Path(arg).read_text() if arg.endswith(".sql") else arg + ";"
    con = db.connect()
    for stmt in statements(text):
        title = next((l[3:].strip() for l in stmt.splitlines() if l.startswith("-- Q")), None)
        if title:
            print(f"== {title}")
        show(con.execute(stmt))
    con.commit()   # keep any INSERT / UPDATE / DELETE you ran


if __name__ == "__main__":
    main()
