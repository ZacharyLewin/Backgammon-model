"""
Ask the database questions in plain English. Claude writes the SQL, you see it,
then it runs (read-only, so nothing can ever be changed or deleted).

    python3 ask.py "how often does each matchup end in a gammon?"
    python3 ask.py --file questions.txt          # one question per line
    python3 ask.py "same question" --mine sql/my_queries.sql   # CHECK MODE

Check mode: write your own attempt first. ask.py runs both versions, tells you
whether the results match, and explains the difference. That's the point —
use it as a tutor, not a crutch.

Every question and answer is appended to sql/ask_log.sql, so you build up a
personal library of worked examples.

Setup (once): get an API key at console.anthropic.com, then in Terminal
    export ANTHROPIC_API_KEY="sk-ant-..."
(add that line to ~/.zshrc so it survives restarts). Never paste the key into
this file or anywhere you share the code.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from bgmodel import db
from run_sql import show

MODEL = "claude-sonnet-5-5"
LOG = db.ROOT / "sql" / "ask_log.sql"


def schema_text(con: sqlite3.Connection) -> str:
    rows = con.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'")
    return "\n\n".join(r[0] for r in rows)


def call_claude(system: str, user: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("No API key found. Run:  export ANTHROPIC_API_KEY=\"sk-ant-...\"  (see the top of ask.py)")
    body = json.dumps({"model": MODEL, "max_tokens": 1500, "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {e.code}: {e.read().decode()[:300]}")
    return "".join(b.get("text", "") for b in data["content"])


SYSTEM = """You translate questions about a backgammon simulation database into SQLite queries.
Rules:
- Reply with exactly one ```sql code block containing ONE read-only SELECT (CTEs allowed),
  then 2-4 short lines explaining each clause in plain English for a SQL learner.
- Use only tables and columns in the schema. Use readable aliases and comment tricky lines.
- If the question can't be answered from this data, say so instead of guessing.

Schema:
{schema}"""

CHECK = """A student wrote their own query for this question. Compare it with yours.
Say plainly whether theirs is correct; if not, name the specific mistake and the smallest
fix, in 3-5 lines. Be encouraging but honest. Results summary: {match}

Question: {q}

Student's SQL:
{mine}

Your SQL:
{theirs}"""


def extract_sql(text: str) -> str:
    m = re.search(r"```sql\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip().rstrip(";")


def run_readonly(sql: str):
    con = sqlite3.connect(f"file:{db.DB_PATH}?mode=ro", uri=True)
    try:
        cur = con.execute(sql)
        return cur, None
    except sqlite3.Error as e:
        return None, str(e)


def results(sql: str):
    cur, err = run_readonly(sql)
    return (None, err) if err else ([tuple(r) for r in cur.fetchall()], None)


def ask(q: str, mine: str | None, con: sqlite3.Connection):
    print(f"\n### {q}\n")
    reply = call_claude(SYSTEM.format(schema=schema_text(con)), q)
    sql = extract_sql(reply)
    explanation = re.sub(r"```sql.*?```", "", reply, flags=re.S).strip()
    print(sql + ";\n")
    if explanation:
        print(explanation + "\n")

    cur, err = run_readonly(sql)
    if err:
        print(f"That query failed: {err}")
    else:
        show(cur)

    if mine:
        mine_rows, mine_err = results(mine)
        claude_rows, _ = results(sql)
        if mine_err:
            match = f"the student's query errors: {mine_err}"
        elif sorted(map(str, mine_rows)) == sorted(map(str, claude_rows or [])):
            match = "both queries return identical rows"
        else:
            match = f"results differ ({len(mine_rows)} rows vs {len(claude_rows or [])})"
        print(f"== Your query: {match}")
        print(call_claude("You are a patient SQL tutor.",
                          CHECK.format(match=match, q=q, mine=mine, theirs=sql)) + "\n")

    with LOG.open("a") as f:
        f.write(f"\n-- {datetime.now():%Y-%m-%d %H:%M}  Q: {q}\n{sql};\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="?")
    ap.add_argument("--file", help="text file with one question per line")
    ap.add_argument("--mine", help="your own attempt: a .sql file or a query in quotes (check mode)")
    args = ap.parse_args()

    questions = []
    if args.file:
        questions = [l.strip() for l in Path(args.file).read_text().splitlines() if l.strip()]
    elif args.question:
        questions = [args.question]
    else:
        ap.error("give a question in quotes, or --file questions.txt")

    mine = None
    if args.mine:
        mine = Path(args.mine).read_text() if args.mine.endswith(".sql") else args.mine
        mine = extract_sql(mine)

    con = db.connect()
    for q in questions:
        ask(q, mine, con)


if __name__ == "__main__":
    main()
