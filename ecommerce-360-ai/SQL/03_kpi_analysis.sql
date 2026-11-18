
-- Executive KPIs
SELECT
  COUNT(DISTINCT order_id) AS orders,
  COUNT(DISTINCT customer_unique_id) AS customers,
  SUM(sales) AS item_sales,
  SUM(freight_value) AS freight,
  SUM(gross_order_value) AS sales_plus_freight,
  SUM(sales)/NULLIF(COUNT(DISTINCT order_id),0) AS aov
FROM analytics.fact_sales
WHERE order_status='delivered';

-- Monthly revenue / order trend
SELECT purchase_month,
       SUM(sales) AS revenue,
       COUNT(DISTINCT order_id) AS orders,
       COUNT(DISTINCT customer_unique_id) AS customers,
       SUM(sales)/NULLIF(COUNT(DISTINCT order_id),0) AS aov
FROM analytics.fact_sales
WHERE order_status='delivered'
GROUP BY purchase_month
ORDER BY purchase_month;

-- Month-over-month growth using a window function
WITH m AS (
 SELECT purchase_month, SUM(sales) revenue
 FROM analytics.fact_sales
 WHERE order_status='delivered'
 GROUP BY purchase_month
)
SELECT purchase_month, revenue,
       LAG(revenue) OVER(ORDER BY purchase_month) previous_month,
       (revenue-LAG(revenue) OVER(ORDER BY purchase_month))
         /NULLIF(LAG(revenue) OVER(ORDER BY purchase_month),0) AS mom_growth
FROM m
ORDER BY purchase_month;
