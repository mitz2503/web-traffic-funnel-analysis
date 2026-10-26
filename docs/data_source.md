# Data source

The store is the Google Merchandise Store, which sells Google-branded
merchandise. The rows are an obfuscated Google Analytics 4 export, not a
scrape of the website and not the live [Google Analytics demo account](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset).
Google says the BigQuery sample and the demo account are different data.
Do not try to make the numbers match.

## What to cite

- Dataset: GA4 obfuscated sample ecommerce
- Project: `bigquery-public-data`
- Table: `ga4_obfuscated_sample_ecommerce.events_*`
- Publisher: Google, through the [BigQuery public dataset program](https://cloud.google.com/bigquery/public-data)
- Documentation: [BigQuery sample dataset for Google Analytics ecommerce](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset)
- Full span of the public sample: 1 November 2020 through 31 January 2021
- This project uses: **7 December 2020 through 13 December 2020** (Monday through Sunday)

Google's documentation describes the file as obfuscated data that emulates a
real GA4 ecommerce export. Some fields are placeholders (`NULL`, blank,
`<Other>`, `(data deleted)`). Internal consistency is limited. Visitor ids
are pseudonymous. There is no separate Creative Commons license on the
dataset. Access to the full sample is "anyone with a Google Cloud project
can query it." The first 1 TB of queries per month is inside the free tier.

## The file in this repo

`data/raw/events.csv.gz` is a one-week slice of a flattened public copy of
that table, published by Dmitrijs Gizdevans as
[gizdevans/ga4-bq-flattened-data](https://huggingface.co/datasets/gizdevans/ga4-bq-flattened-data).
The dataset card on Hugging Face is tagged MIT by the uploader. That tag
covers their packaging. It does not relicense Google's records, and this
project does not claim the rows are MIT or CC BY.

The slice is local so the analysis runs on a laptop without a Google Cloud
account. Counts, the date window, and a SHA256 checksum are in
`data/raw/EXTRACT_INFO.md`.

`scripts/download_extract.py` rebuilds the slice by streaming that flattened
file and keeping the same week. `sql/00_bigquery_extract.sql` is the query
to run in BigQuery if you want the same columns from the canonical table.
Keep `user_pseudo_id` as text if you do that. A spreadsheet will shorten it.

Two limits of this extract belong next to any rate:

1. **The client id was stored as a number** in the flattened file. GA client
   ids are longer than an ordinary number keeps exactly, so two browsers can
   collapse into one `user_pseudo_id`. Session rates (purchases divided by
   sessions) do not need a perfect user count. Unique-user counts from this
   file are weaker. The BigQuery query keeps the id as a string.
2. **The extract is filtered on event date, not session-start date.** A
   session that began before 7 December and continued into that day is only
   partly here, so its landing page or channel can be wrong. `data_quality.md`
   counts sessions with no `session_start` event. A production job filters
   on the session start.

The week is pre-Christmas. It is busy, it contains a weekend, and it is not
an "average" week. Say that when you give a rate.

## What this supports

The claim this project supports is narrow: a public, obfuscated GA4 export of the
Google Merchandise Store for one week in December 2020. The analysis does not
come from administering a GA4 property, and it does not use the Default Channel Group
or a data-driven attribution model from the GA4 interface. The channel
column is a simplified grouping in `scripts/funnel_rules.py`.
