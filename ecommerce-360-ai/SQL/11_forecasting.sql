
-- Forecasting is best done outside SQL in Python/Power BI because Olist's
-- purchase/delivery timestamps create a partially observed final period.
-- Export complete monthly purchase/revenue history to Python.
SELECT purchase_month,
       SUM(sales) revenue,
       COUNT(DISTINCT order_id) orders
FROM analytics.fact_sales
WHERE order_status='delivered'
  AND purchase_month <= DATE '2018-08-01'
GROUP BY purchase_month
ORDER BY purchase_month;
