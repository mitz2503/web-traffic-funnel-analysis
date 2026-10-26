"""Turn raw GA4 events into one row per session.

The output is `data/processed/funnel_sessions.csv`.
SQL and the pandas walkthrough use the same file.

Grain: one row is one session, defined as one user_pseudo_id plus one
ga_session_id. Flags are 1 or 0, so a SUM in Excel is a count of sessions.

Usage:
    python scripts/prepare_sessions.py
"""

import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from funnel_rules import (  # noqa: E402
    STEP_RANK,
    channel_from_referrer,
    channel_group,
    closed_step_flags,
    is_internal_host,
    page_path,
    referrer_host,
)
from project_config import (  # noqa: E402
    DATA_QUALITY,
    DATE_END,
    DATE_START,
    EVENTS_GZ,
    PROCESSED_DIR,
    SESSION_COLUMNS,
    SESSIONS_CSV,
)


def _blank(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"null", "nan", "(not set)"}


def _text(value, default="(not set)"):
    if _blank(value):
        return default
    return str(value).strip()


def _as_int(value):
    text = "" if value is None else str(value).strip()
    if not text or not text.lstrip("-").isdigit():
        return None
    return int(text)


def _as_float(value):
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _first_present(frame, column):
    for value in frame[column].tolist():
        if not _blank(value):
            return str(value).strip()
    return ""


def _session_row(frame):
    """Summarise one session. `frame` is already sorted by time."""
    frame = frame.sort_values(["ts", "step_rank"], kind="mergesort")
    names = frame["event_name"].tolist()
    saw_view, closed_cart, closed_purchase = closed_step_flags(names)

    source = _first_present(frame, "ep_source")
    medium = _first_present(frame, "ep_medium")
    campaign = _first_present(frame, "ep_campaign")
    if source or medium:
        channel = channel_group(source or "(not set)", medium or "(not set)")
        method = "event_params"
    else:
        channel = "(not set)"
        method = ""

    entrance = frame[frame["entrances"] == "1"]
    landing_frame = entrance if len(entrance) else frame
    landing_url = _first_present(landing_frame, "page_location")
    if not landing_url:
        landing_url = _first_present(frame, "page_location")
    referrer_url = _first_present(landing_frame, "page_referrer")
    if not referrer_url:
        referrer_url = _first_present(frame, "page_referrer")
    host = referrer_host(referrer_url)

    if method != "event_params":
        if host and not is_internal_host(host):
            channel = channel_from_referrer(host)
            method = "referrer"
        else:
            channel = "Direct"
            method = "direct_residual"

    user_source = _first_present(frame, "traffic_source")
    user_medium = _first_present(frame, "traffic_medium")
    if user_source or user_medium:
        user_channel = channel_group(user_source or "(not set)", user_medium or "(not set)")
    else:
        user_channel = "(not set)"

    engaged = bool((frame["session_engaged"] == "1").any())
    event_date = str(frame["event_date"].iloc[0])
    session_dt = datetime.strptime(event_date, "%Y%m%d")
    purchase_rows = frame[frame["event_name"] == "purchase"]
    transaction_ids = [
        str(value).strip()
        for value in purchase_rows["ecom_transaction_id"].tolist()
        if not _blank(value)
    ]
    if transaction_ids:
        n_purchase = len(set(transaction_ids))
        # One revenue figure per transaction id. The first row wins.
        seen = set()
        revenue = 0.0
        revenue_seen = False
        for txn, raw_revenue in zip(
            purchase_rows["ecom_transaction_id"].tolist(),
            purchase_rows["ecom_revenue_usd"].tolist(),
        ):
            key = str(txn).strip() if not _blank(txn) else None
            if key is not None:
                if key in seen:
                    continue
                seen.add(key)
            amount = _as_float(raw_revenue)
            if amount is not None:
                revenue += amount
                revenue_seen = True
        revenue_usd = round(revenue, 2) if revenue_seen else ""
    else:
        n_purchase = int((frame["event_name"] == "purchase").sum())
        amounts = [_as_float(value) for value in purchase_rows["ecom_revenue_usd"].tolist()]
        amounts = [value for value in amounts if value is not None]
        revenue_usd = round(sum(amounts), 2) if amounts else ""

    session_number = _as_int(_first_present(frame, "ga_session_number"))
    devices = [str(value).strip() for value in frame["device_category"].tolist() if not _blank(value)]
    browsers = [str(value).strip() for value in frame["browser"].tolist() if not _blank(value)]
    countries = [str(value).strip() for value in frame["country"].tolist() if not _blank(value)]

    return {
        "session_date": session_dt.strftime("%Y-%m-%d"),
        "user_pseudo_id": str(frame["user_pseudo_id"].iloc[0]),
        "ga_session_id": str(frame["ga_session_id"].iloc[0]),
        "session_number": "" if session_number is None else session_number,
        "weekday_name": session_dt.strftime("%A"),
        "device": devices[0] if devices else "(not set)",
        "browser": browsers[0] if browsers else "(not set)",
        "country": countries[0] if countries else "(not set)",
        "channel": channel,
        "channel_method": method,
        "session_source": source or "(not set)",
        "session_medium": medium or "(not set)",
        "session_campaign": campaign or "(not set)",
        "user_channel": user_channel,
        "user_source": user_source or "(not set)",
        "user_medium": user_medium or "(not set)",
        "landing_page": page_path(landing_url),
        "is_bounce": 0 if engaged else 1,
        "is_engaged": 1 if engaged else 0,
        "n_pageviews": int((frame["event_name"] == "page_view").sum()),
        "n_view_item": int((frame["event_name"] == "view_item").sum()),
        "n_add_to_cart": int((frame["event_name"] == "add_to_cart").sum()),
        "n_begin_checkout": int((frame["event_name"] == "begin_checkout").sum()),
        "n_purchase": n_purchase,
        "revenue_usd": revenue_usd,
        "flag_view_item": int(saw_view or (frame["event_name"] == "view_item").any()),
        "flag_add_to_cart": int((frame["event_name"] == "add_to_cart").any()),
        "flag_begin_checkout": int((frame["event_name"] == "begin_checkout").any()),
        "flag_purchase": int((frame["event_name"] == "purchase").any()),
        "flag_closed_add_to_cart": int(closed_cart),
        "flag_closed_purchase": int(closed_purchase),
        "saw_promotion": int(frame["ep_promotion_name"].map(lambda value: not _blank(value)).any()),
        "_device_conflict": int(len(set(devices)) > 1),
        "_has_session_start": int((frame["event_name"] == "session_start").any()),
        "_referrer_host": host or "(none)",
    }


def _quality_report(sessions, events_read, events_dropped):
    n = len(sessions)
    def share(mask):
        return 0 if n == 0 else 100.0 * mask.sum() / n

    method_counts = sessions["channel_method"].value_counts()
    channel_counts = sessions["channel"].value_counts()
    open_purchases = int(sessions["flag_purchase"].sum())
    closed_purchases = int(sessions["flag_closed_purchase"].sum())
    revenue = pd.to_numeric(sessions["revenue_usd"], errors="coerce")
    purchase_sessions = sessions["flag_purchase"] == 1
    lines = [
        "# Data notes",
        "",
        "Checks on the extract for this week.",
        "",
        f"- Date window: {DATE_START} through {DATE_END}.",
        f"- Event rows read: {events_read:,}.",
        f"- Event rows dropped because `user_pseudo_id` or `ga_session_id` was empty: {events_dropped:,}.",
        f"- Sessions (one row each): {n:,}.",
        f"- Users (`user_pseudo_id`, treated as text): {sessions['user_pseudo_id'].nunique():,}.",
        f"- Sessions per user, average: {n / sessions['user_pseudo_id'].nunique():.2f}.",
        f"- Bounce rate (sessions with `is_bounce` = 1): {share(sessions['is_bounce'] == 1):.1f}%.",
        f"- Engaged sessions: {int(sessions['is_engaged'].sum()):,}.",
        "",
        "## Channel method",
        "",
        "How `channel` was filled. `event_params` means the session had a source or medium on an event.",
        "`referrer` means it did not, so the landing referrer was used. `direct_residual` means neither",
        "was available, so the session was labeled Direct. That last bucket is a residual, not proof",
        "that someone typed the URL.",
        "",
    ]
    for method, count in method_counts.items():
        lines.append(f"- {method}: {int(count):,} sessions ({100.0 * count / n:.1f}%).")
    lines.extend(["", "## Channel (session scope)", ""])
    for name, count in channel_counts.items():
        lines.append(f"- {name}: {int(count):,} sessions.")
    lines.extend(
        [
            "",
            "## Where Referral comes from",
            "",
            "`session_source` for sessions labeled Referral. If the store's own hostname is on this list, that traffic is self-referral: the site sent the session to itself. It is not a partner. Decide what you want to do with those rows before you brief anyone on the Referral conversion rate.",
            "",
        ]
    )
    referral_sources = (
        sessions.loc[sessions["channel"] == "Referral", "session_source"]
        .value_counts()
        .head(8)
    )
    if referral_sources.empty:
        lines.append("- No Referral sessions.")
    else:
        for name, count in referral_sources.items():
            lines.append(f"- {name}: {int(count):,}")
    lines.extend(
        [
            "",
            "## Placeholder sources",
            "",
            "Google's public sample replaces some source and medium values with `<Other>` or `(data deleted)`. Those sessions are labeled `(obfuscated)`. Do not describe that label as a marketing channel.",
            "",
        ]
    )
    lines.extend(
        [
            "",
            "## Funnel flags",
            "",
            f"- Open product views (`flag_view_item`): {int(sessions['flag_view_item'].sum()):,}.",
            f"- Open add to cart: {int(sessions['flag_add_to_cart'].sum()):,}.",
            f"- Open begin checkout: {int(sessions['flag_begin_checkout'].sum()):,}.",
            f"- Open purchase: {open_purchases:,}.",
            f"- Closed add to cart (a product view at or before the cart): {int(sessions['flag_closed_add_to_cart'].sum()):,}.",
            f"- Closed purchase (view, then cart, then purchase): {closed_purchases:,}.",
            f"- Purchases in the open funnel that are not in the closed funnel: {open_purchases - closed_purchases:,}.",
            "",
            "The worked example uses the closed funnel. The gap above is a data question, not automatically a bug in your SQL.",
            "",
            "## Revenue",
            "",
        ]
    )
    known = revenue.notna().sum()
    lines.append(f"- Sessions with a non-empty `revenue_usd`: {int(known):,} of {n:,}.")
    if purchase_sessions.any():
        known_purchases = revenue[purchase_sessions].notna().sum()
        lines.append(
            f"- Purchase sessions with a revenue value: {int(known_purchases):,} of {int(purchase_sessions.sum()):,}."
        )
        if known_purchases:
            lines.append(
                f"- Revenue on those sessions, sum: {revenue[purchase_sessions].sum():,.2f} USD. "
                f"Median: {revenue[purchase_sessions].median():,.2f}."
            )
    lines.extend(
        [
            "",
            "## Other checks",
            "",
            f"- Sessions where the device category was not stable inside the session: {int(sessions['_device_conflict'].sum()):,}. The table keeps the earliest non-empty device.",
            f"- Sessions with no `session_start` event inside this date window: {int((sessions['_has_session_start'] == 0).sum()):,}. Some of those started before 7 December, so the landing page and channel can be incomplete. A production extract filters on the session start date, not on every event date.",
            "- Every `user_pseudo_id` in the flattened extract was stored as a number before it reached this project. GA client ids are longer than a spreadsheet number keeps exactly, so two browsers can collapse into one id. The id is text here. Do not sum it. Session rates do not need a perfect user count. For a defensible user count, rebuild from BigQuery with `sql/00_bigquery_extract.sql`, which keeps the id as a string.",
            f"- Landing page `(not set)`: {int((sessions['landing_page'] == '(not set)').sum()):,}.",
            f"- Distinct landing pages: {sessions['landing_page'].nunique():,}.",
            f"- Sessions with `saw_promotion` = 1: {int(sessions['saw_promotion'].sum()):,}.",
            "",
            "Top referrer hosts on the landing hit (internal store hosts included):",
            "",
        ]
    )
    # Referrer hosts were stashed on the frame before we drop helper columns.
    return "\n".join(lines) + "\n"


def prepare():
    if not EVENTS_GZ.exists():
        raise SystemExit(
            f"Missing {EVENTS_GZ}. Run python scripts/download_extract.py first, "
            "or start from the copy shipped in the repo."
        )
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(EVENTS_GZ, dtype=str, keep_default_na=False)
    events_read = len(events)
    missing_id = (events["user_pseudo_id"].map(_blank)) | (events["ga_session_id"].map(_blank))
    events_dropped = int(missing_id.sum())
    events = events.loc[~missing_id].copy()
    events["ts"] = events["event_timestamp"].map(_as_int)
    events = events.loc[events["ts"].notna()].copy()
    events["ts"] = events["ts"].astype("int64")
    events["step_rank"] = events["event_name"].map(lambda name: STEP_RANK.get(name, 9))

    rows = []
    referrer_counts = Counter()
    grouped = events.groupby(["user_pseudo_id", "ga_session_id"], sort=False)
    for _, frame in grouped:
        row = _session_row(frame)
        referrer_counts[row.pop("_referrer_host")] += 1
        rows.append(row)

    sessions = pd.DataFrame(rows)
    sessions = sessions.sort_values(
        ["session_date", "user_pseudo_id", "ga_session_id"]
    ).reset_index(drop=True)
    # Stable column order, then drop the helper after the quality report.
    quality = _quality_report(sessions, events_read, events_dropped)
    top_hosts = "\n".join(
        f"- {host}: {count:,}" for host, count in referrer_counts.most_common(15)
    )
    quality = quality + top_hosts + "\n"
    sessions = sessions[SESSION_COLUMNS]
    sessions.to_csv(SESSIONS_CSV, index=False, encoding="utf-8-sig")
    DATA_QUALITY.write_text(quality, encoding="utf-8")
    print(f"Wrote {SESSIONS_CSV} ({len(sessions):,} sessions)")
    print(f"Wrote {DATA_QUALITY}")
    print(
        "Closed funnel sessions:",
        len(sessions),
        int(sessions["flag_view_item"].sum()),
        int(sessions["flag_closed_add_to_cart"].sum()),
        int(sessions["flag_closed_purchase"].sum()),
    )


if __name__ == "__main__":
    prepare()
