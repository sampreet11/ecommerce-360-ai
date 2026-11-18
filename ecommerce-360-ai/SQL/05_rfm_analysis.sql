
-- RFM scoring.
-- Snapshot should be the maximum observed purchase timestamp in the delivered dataset,
-- not the machine's current date, to avoid time leakage.
WITH snapshot AS (
 SELECT MAX(order_purchase_timestamp) AS snapshot_ts
 FROM analytics.fact_sales
 WHERE order_status='delivered'
),
base AS (
 SELECT c.customer_unique_id,
        (s.snapshot_ts::date - c.last_purchase::date) AS recency_days,
        c.orders AS frequency,
        c.revenue AS monetary
 FROM analytics.customer_360 c CROSS JOIN snapshot s
),
scored AS (
 SELECT *,
   6-NTILE(5) OVER(ORDER BY recency_days) AS r_score,
   NTILE(5) OVER(ORDER BY frequency) AS f_score,
   NTILE(5) OVER(ORDER BY monetary) AS m_score
 FROM base
)
SELECT *,
       r_score+f_score+m_score AS rfm_score,
       CASE
         WHEN r_score>=4 AND f_score>=4 AND m_score>=4 THEN 'Champions'
         WHEN r_score>=3 AND f_score>=4 THEN 'Loyal Customers'
         WHEN r_score>=4 AND f_score<=3 AND frequency>1 THEN 'Potential Loyalists'
         WHEN r_score>=4 AND frequency=1 THEN 'New / Recent One-Time'
         WHEN r_score<=2 AND f_score>=4 AND m_score>=4 THEN 'Can''t Lose Them'
         WHEN r_score<=2 AND f_score>=2 THEN 'At Risk'
         ELSE 'Lapsed / Lost'
       END AS rfm_segment
FROM scored;
