-- Canonical extract from Google's public GA4 Merchandise Store sample.
--
-- Run this in the BigQuery sandbox (a free Google Cloud project, no card
-- required for the free tier). Then export the result as CSV and pass it to:
--   python scripts/download_extract.py --input your_export.csv --force
--
-- The committed data/raw/events.csv.gz was built from a flattened public copy
-- of this same dataset, not by running this query in this repo. Column names
-- match. See docs/data_source.md before you describe the file as "raw GA4".
--
-- Date window: 7 December 2020 through 13 December 2020.
-- Keep user_pseudo_id as a STRING. Do not let a spreadsheet turn it into a number.

SELECT
  event_date,
  event_timestamp,
  event_name,
  user_pseudo_id,
  device.category AS device_category,
  device.web_info.browser AS browser,
  geo.country AS country,
  traffic_source.source AS traffic_source,
  traffic_source.medium AS traffic_medium,
  traffic_source.name AS traffic_campaign,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') AS page_location,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_referrer') AS page_referrer,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'source') AS ep_source,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'medium') AS ep_medium,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'campaign') AS ep_campaign,
  CAST(
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id')
    AS STRING
  ) AS ga_session_id,
  CAST(
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_number')
    AS STRING
  ) AS ga_session_number,
  CAST(
    (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'entrances')
    AS STRING
  ) AS entrances,
  (
    SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING))
    FROM UNNEST(event_params)
    WHERE key = 'session_engaged'
  ) AS session_engaged,
  ecommerce.transaction_id AS ecom_transaction_id,
  ecommerce.purchase_revenue_in_usd AS ecom_revenue_usd,
  (
    SELECT value.string_value
    FROM UNNEST(event_params)
    WHERE key = 'promotion_name'
  ) AS ep_promotion_name
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN '20201207' AND '20201213';
