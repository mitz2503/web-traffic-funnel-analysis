"""Check the funnel pipeline.

Checks the channel rules, the session file, and the worked example.

Usage:
    python scripts/verify.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from funnel_rules import channel_from_referrer, channel_group, closed_step_flags  # noqa: E402
from project_config import (  # noqa: E402
    EVENTS_GZ,
    OUTPUT_DIR,
    SESSION_COLUMNS,
    SESSIONS_CSV,
    WORKED_EXAMPLE_CSV,
)
from run_sql import connect, run_file  # noqa: E402


def check(condition, message):
    if not condition:
        raise SystemExit(f"CHECK FAILED: {message}")


def check_rules():
    check(channel_group("(direct)", "(none)") == "Direct", "direct channel")
    check(channel_group("google", "organic") == "Organic Search", "organic")
    check(channel_group("google", "cpc") == "Paid Search", "paid search")
    check(channel_group("newsletter", "email") == "Email", "email")
    check(channel_group("partner.example", "referral") == "Referral", "referral")
    check(channel_group("facebook", "cpc") == "Paid Social", "paid social")
    check(channel_group("", "") == "(not set)", "empty channel")
    check(channel_group("<Other>", "<Other>") == "(obfuscated)", "placeholder channel")
    check(channel_group("(data deleted)", "(data deleted)") == "(obfuscated)", "deleted channel")
    check(channel_group("<Other>", "referral") == "Referral", "hidden source, known medium")
    check(channel_from_referrer("www.google.com") == "Organic Search", "google referrer")
    check(channel_from_referrer("box.com") == "Referral", "box.com is not x.com")
    check(channel_from_referrer("mail.google.com") == "Referral", "gmail is not search")
    check(
        channel_from_referrer("shop.googlemerchandisestore.com") == "(not set)",
        "internal referrer",
    )
    check(
        closed_step_flags(["view_item", "add_to_cart", "purchase"]) == (True, True, True),
        "ordered closed funnel",
    )
    check(
        closed_step_flags(["add_to_cart", "view_item", "purchase"]) == (True, False, False),
        "cart before view is not a closed purchase",
    )
    check(
        closed_step_flags(["purchase"]) == (False, False, False),
        "purchase alone is open, not closed",
    )
    check(
        closed_step_flags(["view_item", "purchase", "add_to_cart"]) == (True, True, False),
        "a cart after the purchase does not count as a closed purchase",
    )


def check_sessions():
    check(EVENTS_GZ.exists(), "raw extract exists")
    check(SESSIONS_CSV.exists(), "session file exists")
    with SESSIONS_CSV.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        check(reader.fieldnames == SESSION_COLUMNS, "session columns match the schema list")
        rows = list(reader)
    check(len(rows) >= 1000, "expected at least 1000 sessions in this week")
    keys = [(row["user_pseudo_id"], row["ga_session_id"]) for row in rows]
    check(len(keys) == len(set(keys)), "session grain is unique")
    purchases = sum(int(row["flag_closed_purchase"]) for row in rows)
    open_purchases = sum(int(row["flag_purchase"]) for row in rows)
    views = sum(int(row["flag_view_item"]) for row in rows)
    carts = sum(int(row["flag_closed_add_to_cart"]) for row in rows)
    check(purchases >= 50, "expected enough closed purchases for this week")
    check(views >= carts >= purchases, "closed funnel is monotonic")
    check(open_purchases >= purchases, "open purchases cover the closed ones")
    for row in rows:
        for column in ("flag_view_item", "flag_closed_purchase", "is_bounce", "is_engaged"):
            check(row[column] in {"0", "1"}, f"{column} is 0 or 1")
        check(int(row["is_bounce"]) + int(row["is_engaged"]) == 1, "bounce and engaged are opposites")


def main():
    check_rules()
    check_sessions()
    # SQL checks are inline below so the result-set count stays next to the asserts.
    conn = connect()
    worked = run_file("sql/01_worked_example_funnel.sql", conn=conn, echo=False)
    headers, rows = worked[0]
    check(headers[:2] == ["step", "sessions"], "worked example columns")
    check(len(rows) == 4, "worked example has four steps")
    counts = [row["sessions"] for row in rows]
    check(counts[0] >= counts[1] >= counts[2] >= counts[3], "worked example decreases")
    check(counts[3] > 0, "worked example has purchases")
    for row in rows:
        if row["pct_of_previous_step"] is not None:
            check(0 <= row["pct_of_previous_step"] <= 100.0001, "step percent in range")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with WORKED_EXAMPLE_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row[name] for name in headers])

    conn.close()
    print("Setup checks passed.")
    print(f"Worked example written to {WORKED_EXAMPLE_CSV}")


if __name__ == "__main__":
    main()
