-- Reusable analytical views. Portable SQL (PostgreSQL + SQLite for tests).
-- KPI definitions (see docs/data-dictionary.md):
--   revenue = SUM(sales) = SUM(item price). NOT profit. Excludes freight.
--   orders  = COUNT(DISTINCT order_id)  (order grain)
--   Views are delivered-orders-only unless stated.

DROP VIEW IF EXISTS analytics.v_order_level;
CREATE VIEW analytics.v_order_level AS
SELECT order_id,
       MAX(customer_unique_id) AS customer_unique_id,
       MAX(customer_state)     AS customer_state,
       MAX(order_status)       AS order_status,
       MIN(order_purchase_timestamp) AS purchase_ts,
       MIN(purchase_month)     AS purchase_month,
       COUNT(*)                AS items,
       SUM(sales)              AS revenue,
       SUM(freight_value)      AS freight,
       MAX(delivery_days)      AS delivery_days,
       MAX(late_flag)          AS late_flag
FROM analytics.fact_sales
GROUP BY order_id;

DROP VIEW IF EXISTS analytics.v_monthly_kpis;
CREATE VIEW analytics.v_monthly_kpis AS
SELECT purchase_month,
       SUM(revenue) AS revenue, SUM(freight) AS freight, SUM(items) AS items,
       COUNT(*) AS orders, COUNT(DISTINCT customer_unique_id) AS customers,
       SUM(revenue) * 1.0 / NULLIF(COUNT(*), 0) AS aov
FROM analytics.v_order_level
WHERE order_status = 'delivered'
GROUP BY purchase_month;

DROP VIEW IF EXISTS analytics.v_category_kpis;
CREATE VIEW analytics.v_category_kpis AS
SELECT category,
       SUM(sales) AS revenue, SUM(freight_value) AS freight, COUNT(*) AS items,
       COUNT(DISTINCT order_id) AS orders, COUNT(DISTINCT customer_unique_id) AS customers,
       SUM(sales) * 1.0 / NULLIF(COUNT(DISTINCT order_id), 0) AS aov
FROM analytics.fact_sales
WHERE order_status = 'delivered'
GROUP BY category;

DROP VIEW IF EXISTS analytics.v_delivery_by_state;
CREATE VIEW analytics.v_delivery_by_state AS
SELECT customer_state,
       COUNT(*) AS orders,
       AVG(delivery_days) AS avg_delivery_days,
       SUM(late_flag) AS late_orders,
       AVG(late_flag * 1.0) AS late_rate
FROM analytics.v_order_level
WHERE order_status = 'delivered' AND delivery_days IS NOT NULL
GROUP BY customer_state;

DROP VIEW IF EXISTS analytics.v_status_distribution;
CREATE VIEW analytics.v_status_distribution AS
SELECT order_status, COUNT(*) AS orders, SUM(revenue) AS revenue
FROM analytics.v_order_level GROUP BY order_status;

DROP VIEW IF EXISTS analytics.v_seller_performance;
CREATE VIEW analytics.v_seller_performance AS
SELECT seller_id, MAX(seller_state) AS seller_state,
       COUNT(*) AS orders, SUM(rev) AS revenue,
       AVG(delivery_days) AS avg_delivery_days,
       SUM(late) AS late_orders, AVG(late * 1.0) AS late_rate
FROM (
  SELECT order_id, seller_id, MAX(seller_state) AS seller_state, SUM(sales) AS rev,
         MAX(delivery_days) AS delivery_days, MAX(late_flag) AS late
  FROM analytics.fact_sales
  WHERE order_status = 'delivered' AND delivery_days IS NOT NULL
  GROUP BY order_id, seller_id
) s
GROUP BY seller_id;

DROP VIEW IF EXISTS analytics.v_rfm_segments;
CREATE VIEW analytics.v_rfm_segments AS
SELECT rfm_segment, COUNT(*) AS customers, SUM(revenue) AS revenue,
       AVG(orders * 1.0) AS avg_orders, AVG(recency_days * 1.0) AS avg_recency_days,
       AVG(revenue * 1.0) AS avg_revenue_per_customer
FROM analytics.customer_360 GROUP BY rfm_segment;

DROP VIEW IF EXISTS analytics.v_lifecycle;
CREATE VIEW analytics.v_lifecycle AS
SELECT lifecycle, COUNT(*) AS customers, SUM(revenue) AS historical_revenue
FROM analytics.customer_360 GROUP BY lifecycle;
