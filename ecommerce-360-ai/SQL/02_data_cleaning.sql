
-- Cleaning / conformance checks
DROP TABLE IF EXISTS analytics.fact_sales;
CREATE TABLE analytics.fact_sales AS
SELECT
    oi.order_id,
    oi.order_item_id,
    o.customer_id,
    c.customer_unique_id,
    oi.product_id,
    oi.seller_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    oi.price,
    oi.freight_value,
    oi.price AS sales,
    oi.price + oi.freight_value AS gross_order_value,
    COALESCE(t.product_category_name_english,p.product_category_name,'Unknown') AS category,
    c.customer_state,
    s.seller_state,
    EXTRACT(EPOCH FROM
        (o.order_delivered_customer_date-o.order_purchase_timestamp))/86400.0 AS delivery_days,
    EXTRACT(EPOCH FROM
        (o.order_delivered_customer_date-o.order_estimated_delivery_date))/86400.0 AS late_days,
    CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END AS late_flag,
    DATE_TRUNC('month',o.order_purchase_timestamp)::date AS purchase_month
FROM olist.order_items oi
JOIN olist.orders o ON oi.order_id=o.order_id
LEFT JOIN olist.customers c ON o.customer_id=c.customer_id
LEFT JOIN olist.products p ON oi.product_id=p.product_id
LEFT JOIN olist.category_translation t ON p.product_category_name=t.product_category_name
LEFT JOIN olist.sellers s ON oi.seller_id=s.seller_id;

CREATE INDEX IF NOT EXISTS ix_fact_customer ON analytics.fact_sales(customer_unique_id);
CREATE INDEX IF NOT EXISTS ix_fact_order ON analytics.fact_sales(order_id);
CREATE INDEX IF NOT EXISTS ix_fact_month ON analytics.fact_sales(purchase_month);

-- Data-quality checks
SELECT 'duplicate order-item keys' AS check_name, COUNT(*) AS failures
FROM (
  SELECT order_id, order_item_id
  FROM analytics.fact_sales
  GROUP BY order_id, order_item_id
  HAVING COUNT(*)>1
) x;

SELECT 'negative sales' AS check_name, COUNT(*) AS failures
FROM analytics.fact_sales WHERE sales < 0;

SELECT 'delivered without delivery date' AS check_name, COUNT(*) AS failures
FROM analytics.fact_sales
WHERE order_status='delivered' AND order_delivered_customer_date IS NULL;

-- Important analytical limitation:
-- Olist has no product cost and no discount field. Do not calculate "true profit"
-- or "discount impact" as factual metrics. Use sales/freight economics instead.
