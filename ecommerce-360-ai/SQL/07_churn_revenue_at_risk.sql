
-- Olist is not a subscription business and the dataset ends in 2018.
-- Therefore use "lapsed" rather than claiming observed churn.
WITH snapshot AS (
 SELECT MAX(order_purchase_timestamp)::date snapshot_date
 FROM analytics.fact_sales WHERE order_status='delivered'
)
SELECT
  CASE
    WHEN (snapshot_date-last_purchase::date)>=180 THEN 'Lapsed >=180d'
    WHEN (snapshot_date-last_purchase::date)>=90 THEN 'Recently inactive 90-179d'
    ELSE 'Recent <90d'
  END lifecycle,
  COUNT(*) customers,
  SUM(revenue) historical_revenue
FROM analytics.customer_360 CROSS JOIN snapshot
GROUP BY 1
ORDER BY historical_revenue DESC;

-- High-value lapsed customers: a defensible retention target
WITH snapshot AS (
 SELECT MAX(order_purchase_timestamp)::date snapshot_date
 FROM analytics.fact_sales WHERE order_status='delivered'
)
SELECT customer_unique_id, orders, revenue, last_purchase,
       snapshot_date-last_purchase::date AS days_since_purchase
FROM analytics.customer_360 CROSS JOIN snapshot
WHERE (snapshot_date-last_purchase::date)>=180
ORDER BY revenue DESC
LIMIT 100;
