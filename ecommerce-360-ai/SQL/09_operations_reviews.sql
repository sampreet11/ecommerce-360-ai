-- Order-level delivery performance.
-- fact_sales is one row per order item, so first collapse to one row per order.
WITH order_delivery AS (
 SELECT order_id,
        MAX(delivery_days) FILTER (WHERE delivery_days IS NOT NULL) AS delivery_days,
        MAX(late_flag::int) AS late_flag,
        MAX(customer_state) AS customer_state
 FROM analytics.fact_sales
 WHERE order_status='delivered'
 GROUP BY order_id
)
SELECT COUNT(*) AS orders,
       AVG(delivery_days) AS avg_delivery_days,
       AVG(late_flag::numeric) AS late_rate
FROM order_delivery
WHERE delivery_days IS NOT NULL;

-- Customer-state delivery performance; each delivered order counts once.
WITH order_delivery AS (
 SELECT order_id,
        MAX(delivery_days) FILTER (WHERE delivery_days IS NOT NULL) AS delivery_days,
        MAX(late_flag::int) AS late_flag,
        MAX(customer_state) AS customer_state
 FROM analytics.fact_sales
 WHERE order_status='delivered'
 GROUP BY order_id
)
SELECT customer_state, COUNT(*) AS orders,
       AVG(delivery_days) AS avg_delivery_days,
       AVG(late_flag::numeric) AS late_rate
FROM order_delivery
WHERE delivery_days IS NOT NULL
GROUP BY customer_state
HAVING COUNT(*) >= 250
ORDER BY late_rate DESC;

-- Review-score distribution; reviews remain at review-row grain.
SELECT review_score, COUNT(*) AS reviews
FROM olist.order_reviews
GROUP BY review_score
ORDER BY review_score;
