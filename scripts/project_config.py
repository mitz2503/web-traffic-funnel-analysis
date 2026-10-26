"""Paths, dates, and column lists shared by the scripts.

The analysis uses one week of the public GA4 Merchandise Store sample:
Monday 7 December 2020 through Sunday 13 December 2020.

That week is busy enough for channel and device splits, it includes a
weekend, and it stays small enough for a laptop. It is also pre-Christmas,
so the rates are not a "typical" week. Say that when you present the work.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATE_START = "20201207"
DATE_END = "20201213"

# Flattened public copy of bigquery-public-data.ga4_obfuscated_sample_ecommerce.
# See docs/data_source.md for the citation and the license limits.
HF_FLATTENED_CSV_URL = (
    "https://huggingface.co/datasets/gizdevans/ga4-bq-flattened-data"
    "/resolve/main/full_flatten_data.csv"
)

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"

EVENTS_GZ = RAW_DIR / "events.csv.gz"
EVENTS_PREVIEW = RAW_DIR / "events_preview.csv"
EXTRACT_INFO = RAW_DIR / "EXTRACT_INFO.md"
SESSIONS_CSV = PROCESSED_DIR / "funnel_sessions.csv"
DATA_QUALITY = PROCESSED_DIR / "data_quality.md"
WORKED_EXAMPLE_CSV = OUTPUT_DIR / "worked_example_funnel.csv"

# Columns kept from the flattened event export. Names match that file.
RAW_COLUMNS = [
    "event_date",
    "event_timestamp",
    "event_name",
    "user_pseudo_id",
    "device_category",
    "browser",
    "country",
    "traffic_source",
    "traffic_medium",
    "traffic_campaign",
    "page_location",
    "page_referrer",
    "ep_source",
    "ep_medium",
    "ep_campaign",
    "ga_session_id",
    "ga_session_number",
    "entrances",
    "session_engaged",
    "ecom_transaction_id",
    "ecom_revenue_usd",
    "ep_promotion_name",
]

# One row per session. This is the file you open in Excel and query in SQL.
SESSION_COLUMNS = [
    "session_date",
    "user_pseudo_id",
    "ga_session_id",
    "session_number",
    "weekday_name",
    "device",
    "browser",
    "country",
    "channel",
    "channel_method",
    "session_source",
    "session_medium",
    "session_campaign",
    "user_channel",
    "user_source",
    "user_medium",
    "landing_page",
    "is_bounce",
    "is_engaged",
    "n_pageviews",
    "n_view_item",
    "n_add_to_cart",
    "n_begin_checkout",
    "n_purchase",
    "revenue_usd",
    "flag_view_item",
    "flag_add_to_cart",
    "flag_begin_checkout",
    "flag_purchase",
    "flag_closed_add_to_cart",
    "flag_closed_purchase",
    "saw_promotion",
]
