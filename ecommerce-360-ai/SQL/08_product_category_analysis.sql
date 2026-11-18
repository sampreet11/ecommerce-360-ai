
SELECT category,
       SUM(sales) revenue,
       SUM(freight_value) freight,
       COUNT(DISTINCT order_id) orders,
       COUNT(DISTINCT customer_unique_id) customers,
       SUM(sales)/NULLIF(COUNT(DISTINCT order_id),0) aov
FROM analytics.fact_sales
WHERE order_status='delivered'
GROUP BY category
ORDER BY revenue DESC;

-- Revenue concentration
WITH cat AS (
 SELECT category, SUM(sales) revenue
 FROM analytics.fact_sales
 WHERE order_status='delivered'
 GROUP BY category
),
ranked AS (
 SELECT *, SUM(revenue) OVER(ORDER BY revenue DESC
       ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) cumulative_revenue,
       SUM(revenue) OVER() total_revenue
 FROM cat
)
SELECT *, cumulative_revenue/total_revenue cumulative_share
FROM ranked
ORDER BY revenue DESC;
