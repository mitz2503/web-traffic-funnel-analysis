"""Download a one-week event extract from the public GA4 sample.

You do not need to run this if `data/raw/events.csv.gz` is already in the
repo. Run it when you want to rebuild that file yourself.

The script streams a flattened copy of Google's public dataset
`bigquery-public-data.ga4_obfuscated_sample_ecommerce` and keeps only
7–13 December 2020. It does not save the full multi-gigabyte file.

The canonical query, if you have a free BigQuery sandbox, is
`sql/00_bigquery_extract.sql`. See `docs/data_source.md`.

Usage:
    python scripts/download_extract.py
    python scripts/download_extract.py --force
    python scripts/download_extract.py --input /path/to/local.csv
"""

import argparse
import csv
import gzip
import hashlib
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from project_config import (  # noqa: E402
    DATE_END,
    DATE_START,
    EVENTS_GZ,
    EVENTS_PREVIEW,
    EXTRACT_INFO,
    HF_FLATTENED_CSV_URL,
    RAW_COLUMNS,
    RAW_DIR,
)


class _LineReader:
    """Yield text lines from a binary HTTP or file stream."""

    def __init__(self, binary):
        self._binary = binary
        self._pending = ""
        self._decoder_error = "replace"

    def __iter__(self):
        import codecs

        decoder = codecs.getincrementaldecoder("utf-8")(self._decoder_error)
        while True:
            while "\n" in self._pending:
                line, self._pending = self._pending.split("\n", 1)
                yield line
            chunk = self._binary.read(1024 * 256)
            if not chunk:
                self._pending += decoder.decode(b"", final=True)
                if self._pending:
                    line, self._pending = self._pending, ""
                    yield line
                return
            self._pending += decoder.decode(chunk)


def _open_source(input_path):
    if input_path:
        path = Path(input_path)
        if path.suffix == ".gz":
            return gzip.open(path, "rb"), f"local file {path}"
        return open(path, "rb"), f"local file {path}"
    request = urllib.request.Request(
        HF_FLATTENED_CSV_URL,
        headers={"User-Agent": "web-traffic-funnel-analysis"},
    )
    return urllib.request.urlopen(request, timeout=120), HF_FLATTENED_CSV_URL


def _in_window(event_date):
    return len(event_date) == 8 and event_date.isdigit() and DATE_START <= event_date <= DATE_END


def download(force=False, input_path=None):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if EVENTS_GZ.exists() and not force and input_path is None:
        print(f"Extract already exists: {EVENTS_GZ}")
        print("Pass --force to download it again.")
        return

    print("Streaming the public GA4 extract. This reads about 1.8 GB of network")
    print("and keeps one week. It often takes a few minutes.")
    binary, source_label = _open_source(input_path)
    kept = 0
    skipped_short = 0
    skipped_date = 0
    purchases = 0
    sessions = set()
    preview_rows = []

    try:
        reader = csv.reader(_LineReader(binary))
        header = next(reader)
        index = {name: pos for pos, name in enumerate(header)}
        missing = [name for name in RAW_COLUMNS if name not in index]
        if missing:
            raise SystemExit(
                "The source file is missing expected columns: " + ", ".join(missing)
            )

        with gzip.open(EVENTS_GZ, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=RAW_COLUMNS)
            writer.writeheader()
            for row in reader:
                if len(row) < len(header):
                    skipped_short += 1
                    continue
                event_date = row[index["event_date"]]
                if not _in_window(event_date):
                    skipped_date += 1
                    continue
                record = {name: row[index[name]] for name in RAW_COLUMNS}
                writer.writerow(record)
                kept += 1
                if record["event_name"] == "purchase":
                    purchases += 1
                session_id = record["ga_session_id"]
                user_id = record["user_pseudo_id"]
                if session_id and user_id:
                    sessions.add((user_id, session_id))
                if len(preview_rows) < 200:
                    preview_rows.append(record)
                if kept % 100000 == 0:
                    print(f"  kept {kept:,} events", flush=True)
    finally:
        binary.close()

    if kept == 0:
        raise SystemExit(
            "No events were kept. The date window or the source columns may have changed."
        )

    with EVENTS_PREVIEW.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_COLUMNS)
        writer.writeheader()
        writer.writerows(preview_rows)

    digest = hashlib.sha256(EVENTS_GZ.read_bytes()).hexdigest()
    info = f"""# Event extract

Built: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

This is a date slice of a flattened public copy of Google's GA4 Merchandise
Store sample. It is the input to `scripts/prepare_sessions.py`. It is not the
finished analysis.

- Source streamed: `{source_label}`
- Canonical table: `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
- Date window: {DATE_START} through {DATE_END} (inclusive)
- Events kept: {kept:,}
- Purchase events kept: {purchases:,}
- Distinct (user, session) pairs with both ids present: {len(sessions):,}
- Rows skipped (outside the date window, or a bad date): {skipped_date:,}
- Rows skipped (fewer columns than the header): {skipped_short:,}
- SHA256 of `events.csv.gz`: `{digest}`
- Preview: `events_preview.csv` is the first 200 kept rows, in source order.
  Do not compute rates from the preview.

Rebuild with `python scripts/download_extract.py --force`.
Full citation and license limits: `docs/data_source.md`.
"""
    EXTRACT_INFO.write_text(info, encoding="utf-8")
    print(f"Wrote {EVENTS_GZ} ({EVENTS_GZ.stat().st_size / 1e6:.1f} MB)")
    print(f"Events kept: {kept:,}. Purchase events: {purchases:,}.")
    print(f"SHA256 {digest}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download again even if data/raw/events.csv.gz exists.",
    )
    parser.add_argument(
        "--input",
        help="Filter a local CSV or CSV.GZ instead of streaming the public URL.",
    )
    args = parser.parse_args()
    download(force=args.force, input_path=args.input)


if __name__ == "__main__":
    main()
