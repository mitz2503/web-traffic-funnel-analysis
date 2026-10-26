-- Closed funnel: sessions -> product view -> add to cart -> purchase.
--
-- Check the result against outputs/worked_example_funnel.csv.
--
-- Closed funnel, used below:
--   1. Every session counts.
--   2. Product view: the session has a view_item event.
--   3. Add to cart: a view_item happens at or before an add_to_cart.
--   4. Purchase: that cart happens at or before a purchase.
--
-- A session can purchase without passing step 3. Those purchases stay in the
-- open funnel (the second query) and out of the closed one. That gap is a
-- property of the tracking.

WITH steps AS (
  SELECT 1 AS step_order, '1. Session' AS step, COUNT(*) AS sessions
  FROM sessions
  UNION ALL
  SELECT 2, '2. Product view', SUM(flag_view_item) FROM sessions
  UNION ALL
  SELECT 3, '3. Add to cart', SUM(flag_closed_add_to_cart) FROM sessions
  UNION ALL
  SELECT 4, '4. Purchase', SUM(flag_closed_purchase) FROM sessions
)
SELECT
  step,
  sessions,
  -- 1.0 forces real division. In SQLite, integer / integer drops the fraction.
  ROUND(100.0 * sessions / FIRST_VALUE(sessions) OVER (ORDER BY step_order), 2)
    AS pct_of_sessions,
  ROUND(
    100.0 * sessions / NULLIF(LAG(sessions) OVER (ORDER BY step_order), 0),
    2
  ) AS pct_of_previous_step
FROM steps
ORDER BY step_order;

-- Open funnel: the event happened, with no requirement about order.
-- Compare flag_purchase here with step 4 above before you write a finding.
SELECT
  'open_product_view' AS metric,
  SUM(flag_view_item) AS sessions
FROM sessions
UNION ALL
SELECT 'open_add_to_cart', SUM(flag_add_to_cart) FROM sessions
UNION ALL
SELECT 'open_purchase', SUM(flag_purchase) FROM sessions
UNION ALL
SELECT 'closed_purchase', SUM(flag_closed_purchase) FROM sessions;
