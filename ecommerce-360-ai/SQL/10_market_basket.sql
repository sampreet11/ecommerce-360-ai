
-- Category-pair co-occurrence.
-- Category-level basket analysis is intentionally used to keep the project
-- interpretable; product-level association rules can be added later.
WITH order_categories AS (
 SELECT order_id, category
 FROM analytics.fact_sales
 WHERE order_status='delivered'
 GROUP BY order_id, category
),
pairs AS (
 SELECT a.category category_a, b.category category_b,
        COUNT(DISTINCT a.order_id) orders_together
 FROM order_categories a
 JOIN order_categories b
   ON a.order_id=b.order_id AND a.category < b.category
 GROUP BY a.category,b.category
),
orders AS (
 SELECT COUNT(DISTINCT order_id) total_orders
 FROM analytics.fact_sales WHERE order_status='delivered'
)
SELECT p.*,
       orders_together::numeric/NULLIF(o.total_orders,0) support
FROM pairs p CROSS JOIN orders o
ORDER BY orders_together DESC;
