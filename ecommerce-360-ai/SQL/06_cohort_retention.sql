
WITH first_purchase AS (
 SELECT customer_unique_id,
        DATE_TRUNC('month',MIN(order_purchase_timestamp))::date cohort_month
 FROM analytics.fact_sales
 WHERE order_status='delivered'
 GROUP BY customer_unique_id
),
activity AS (
 SELECT DISTINCT f.customer_unique_id,
        fp.cohort_month,
        DATE_TRUNC('month',f.order_purchase_timestamp)::date activity_month
 FROM analytics.fact_sales f
 JOIN first_purchase fp USING(customer_unique_id)
 WHERE f.order_status='delivered'
),
indexed AS (
 SELECT *,
   (EXTRACT(YEAR FROM activity_month)-EXTRACT(YEAR FROM cohort_month))*12 +
   EXTRACT(MONTH FROM activity_month)-EXTRACT(MONTH FROM cohort_month) AS cohort_index
 FROM activity
),
cohort_size AS (
 SELECT cohort_month, COUNT(DISTINCT customer_unique_id) cohort_size
 FROM first_purchase GROUP BY cohort_month
)
SELECT cohort_month, cohort_index,
       COUNT(DISTINCT customer_unique_id) active_customers,
       cohort_size,
       COUNT(DISTINCT customer_unique_id)::numeric/NULLIF(cohort_size,0) retention
FROM indexed
JOIN cohort_size USING(cohort_month)
GROUP BY cohort_month, cohort_index, cohort_size
ORDER BY cohort_month, cohort_index;
