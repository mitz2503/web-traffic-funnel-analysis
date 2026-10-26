"""Pandas version of the closed funnel.

Run from anywhere:

    python notebooks/01_funnel_walkthrough.py

This is the same funnel as sql/01_worked_example_funnel.sql.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def funnel(sessions):
    steps = pd.DataFrame(
        {
            "step": [
                "1. Session",
                "2. Product view",
                "3. Add to cart",
                "4. Purchase",
            ],
            "sessions": [
                len(sessions),
                int(sessions["flag_view_item"].sum()),
                int(sessions["flag_closed_add_to_cart"].sum()),
                int(sessions["flag_closed_purchase"].sum()),
            ],
        }
    )
    base = steps["sessions"].iloc[0]
    steps["pct_of_sessions"] = (100 * steps["sessions"] / base).round(2)
    steps["pct_of_previous_step"] = (
        100 * steps["sessions"] / steps["sessions"].shift(1)
    ).round(2)
    return steps


def main():
    path = ROOT / "data" / "processed" / "funnel_sessions.csv"
    sessions = pd.read_csv(path)
    print(f"{len(sessions):,} sessions. One row is one session.")
    print("Closed funnel: session, then view_item, then add_to_cart, then purchase.")
    print()
    steps = funnel(sessions)
    print(steps.to_string(index=False))
    print()
    check_path = ROOT / "outputs" / "worked_example_funnel.csv"
    if check_path.exists():
        check = pd.read_csv(check_path)
        merged = steps.merge(check, on="step", suffixes=("_pandas", "_sql"))
        if not (merged["sessions_pandas"] == merged["sessions_sql"]).all():
            raise SystemExit("Pandas counts do not match the SQL worked example.")
        print("Session counts match outputs/worked_example_funnel.csv.")
    open_purchases = int(sessions["flag_purchase"].sum())
    closed_purchases = int(sessions["flag_closed_purchase"].sum())
    print(
        f"Open purchases: {open_purchases:,}. "
        f"Closed purchases: {closed_purchases:,}. "
        f"Gap: {open_purchases - closed_purchases:,}."
    )
    print(
        "The gap is sessions that purchased without a view, then a cart, "
        "then the purchase, in that order."
    )


if __name__ == "__main__":
    main()
