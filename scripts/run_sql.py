"""Load the session table and run a SQL file.

Usage:
    python scripts/run_sql.py sql/01_worked_example_funnel.sql

SQLite is used so the SQL runs without a separate database install. SQRT is
registered here because SQLite does not provide it.
"""

import csv
import math
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from project_config import ROOT, SESSIONS_CSV  # noqa: E402

SCHEMA_PATH = ROOT / "sql" / "00_schema.sql"
INTEGER_COLUMNS = {
    "session_number",
    "is_bounce",
    "is_engaged",
    "n_pageviews",
    "n_view_item",
    "n_add_to_cart",
    "n_begin_checkout",
    "n_purchase",
    "flag_view_item",
    "flag_add_to_cart",
    "flag_begin_checkout",
    "flag_purchase",
    "flag_closed_add_to_cart",
    "flag_closed_purchase",
    "saw_promotion",
}
REAL_COLUMNS = {"revenue_usd"}


def connect():
    if not SESSIONS_CSV.exists():
        raise SystemExit(
            f"Missing {SESSIONS_CSV}. Run python scripts/prepare_sessions.py first."
        )
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.create_function("SQRT", 1, math.sqrt)
    conn.create_function("sqrt", 1, math.sqrt)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript("DROP TABLE IF EXISTS sessions;\n" + schema)
    with SESSIONS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        placeholders = ", ".join("?" for _ in columns)
        quoted = ", ".join(columns)
        rows = []
        for record in reader:
            values = []
            for column in columns:
                raw = record[column]
                if raw == "":
                    values.append(None)
                elif column in INTEGER_COLUMNS:
                    values.append(int(float(raw)))
                elif column in REAL_COLUMNS:
                    values.append(float(raw))
                else:
                    values.append(raw)
            rows.append(values)
    conn.executemany(
        f"INSERT INTO sessions ({quoted}) VALUES ({placeholders})",
        rows,
    )
    conn.commit()
    return conn


def statements(sql_text):
    chunks = []
    current = []
    for line in sql_text.splitlines():
        current.append(line)
        if line.rstrip().endswith(";"):
            chunks.append("\n".join(current))
            current = []
    if any(line.strip() for line in current):
        chunks.append("\n".join(current))
    cleaned = []
    for chunk in chunks:
        stripped = "\n".join(
            line for line in chunk.splitlines() if not line.strip().startswith("--")
        ).strip()
        if stripped:
            cleaned.append(chunk)
    return cleaned


def format_table(headers, rows):
    rendered = [["" if value is None else str(value) for value in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in rendered:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    def fmt(row):
        return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
    lines = [fmt(headers), fmt("-" * width for width in widths)]
    lines.extend(fmt(row) for row in rendered)
    return "\n".join(lines)


def run_file(path, conn=None, echo=True):
    sql_path = Path(path)
    if not sql_path.is_absolute():
        sql_path = ROOT / sql_path
    own_connection = conn is None
    if own_connection:
        conn = connect()
    results = []
    try:
        for statement in statements(sql_path.read_text(encoding="utf-8")):
            cursor = conn.execute(statement)
            if cursor.description is None:
                continue
            headers = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            results.append((headers, rows))
            if echo:
                print(f"\n-- {sql_path.relative_to(ROOT)}")
                if not rows:
                    print("(no rows)")
                else:
                    shown = rows[:100]
                    print(format_table(headers, shown))
                    if len(rows) > 100:
                        print(f"... {len(rows) - 100} more rows not shown")
    finally:
        if own_connection:
            conn.close()
    return results


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/run_sql.py path/to/file.sql")
    run_file(sys.argv[1])


if __name__ == "__main__":
    main()
