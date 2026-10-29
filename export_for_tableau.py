"""
Write the tables Tableau needs as CSV files in exports/.
Tableau Public (free, Mac and Windows) opens CSVs directly: Connect -> Text file.

    python export_for_tableau.py
"""
import csv

from bgmodel import db

EXPORTS = db.ROOT / "exports"

QUERIES = {
    "keith_study": "SELECT * FROM keith_study",
    "race_study": "SELECT * FROM v_race_study",
    "games": """
        SELECT g.*, w.name AS white_strategy, b.name AS black_strategy
        FROM games g
        JOIN strategies w ON w.strategy_id = g.white_strategy_id
        JOIN strategies b ON b.strategy_id = g.black_strategy_id""",
    "turns": """
        SELECT t.*, CASE WHEN g.winner = t.player THEN 1 ELSE 0 END AS mover_won
        FROM turns t JOIN games g USING (game_id)""",
}


def main():
    EXPORTS.mkdir(exist_ok=True)
    con = db.connect()
    for name, sql in QUERIES.items():
        cur = con.execute(sql)
        path = EXPORTS / f"{name}.csv"
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow([c[0] for c in cur.description])
            n = 0
            for row in cur:
                w.writerow(row)
                n += 1
        print(f"  {path.relative_to(db.ROOT)}  ({n:,} rows)")


if __name__ == "__main__":
    main()
