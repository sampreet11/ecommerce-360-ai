
-- Customer 360
DROP TABLE IF EXISTS analytics.customer_360;
CREATE TABLE analytics.customer_360 AS
WITH base AS (
 SELECT
   customer_unique_id,
   MIN(order_purchase_timestamp) first_purchase,
   MAX(order_purchase_timestamp) last_purchase,
   COUNT(DISTINCT order_id) orders,
   COUNT(*) items,
   SUM(sales) revenue,
   SUM(freight_value) freight
 FROM analytics.fact_sales
 WHERE order_status='delivered'
 GROUP BY customer_unique_id
),
snapshot AS (
 SELECT MAX(order_purchase_timestamp)::date AS snapshot_date
 FROM analytics.fact_sales
 WHERE order_status='delivered'
),
scored AS (
 SELECT b.*, (s.snapshot_date - b.last_purchase::date) AS recency_days,
        s.snapshot_date
 FROM base b CROSS JOIN snapshot s
)
SELECT *,
       revenue/NULLIF(orders,0) AS aov,
       CASE WHEN orders>1 THEN 1 ELSE 0 END AS repeat_flag,
       DATE_TRUNC('month',first_purchase)::date AS cohort_month
FROM scored;

-- New vs returning
SELECT repeat_flag,
       COUNT(*) customers,
       SUM(revenue) revenue,
       SUM(revenue)/SUM(SUM(revenue)) OVER() revenue_share
FROM analytics.customer_360
GROUP BY repeat_flag;

-- Top customers
SELECT *
FROM analytics.customer_360
ORDER BY revenue DESC
LIMIT 25;
