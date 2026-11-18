
-- E-Commerce 360 Analytics
-- PostgreSQL-oriented schema. Import the 9 raw Olist CSVs into these tables.
CREATE SCHEMA IF NOT EXISTS olist;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS olist.customers (
 customer_id TEXT PRIMARY KEY, customer_unique_id TEXT NOT NULL,
 customer_zip_code_prefix INT, customer_city TEXT, customer_state TEXT
);
CREATE TABLE IF NOT EXISTS olist.geolocation (
 geolocation_zip_code_prefix INT, geolocation_lat NUMERIC,
 geolocation_lng NUMERIC, geolocation_city TEXT, geolocation_state TEXT
);
CREATE TABLE IF NOT EXISTS olist.orders (
 order_id TEXT PRIMARY KEY, customer_id TEXT, order_status TEXT,
 order_purchase_timestamp TIMESTAMP, order_approved_at TIMESTAMP,
 order_delivered_carrier_date TIMESTAMP, order_delivered_customer_date TIMESTAMP,
 order_estimated_delivery_date TIMESTAMP
);
CREATE TABLE IF NOT EXISTS olist.order_items (
 order_id TEXT, order_item_id INT, product_id TEXT, seller_id TEXT,
 shipping_limit_date TIMESTAMP, price NUMERIC(12,2), freight_value NUMERIC(12,2),
 PRIMARY KEY(order_id, order_item_id)
);
CREATE TABLE IF NOT EXISTS olist.order_payments (
 order_id TEXT, payment_sequential INT, payment_type TEXT,
 payment_installments INT, payment_value NUMERIC(12,2)
);
CREATE TABLE IF NOT EXISTS olist.order_reviews (
 review_id TEXT, order_id TEXT, review_score INT,
 review_comment_title TEXT, review_comment_message TEXT,
 review_creation_date TIMESTAMP, review_answer_timestamp TIMESTAMP
);
CREATE TABLE IF NOT EXISTS olist.products (
 product_id TEXT PRIMARY KEY, product_category_name TEXT,
 product_name_lenght INT, product_description_lenght INT,
 product_photos_qty INT, product_weight_g NUMERIC,
 product_length_cm NUMERIC, product_height_cm NUMERIC, product_width_cm NUMERIC
);
CREATE TABLE IF NOT EXISTS olist.sellers (
 seller_id TEXT PRIMARY KEY, seller_zip_code_prefix INT,
 seller_city TEXT, seller_state TEXT
);
CREATE TABLE IF NOT EXISTS olist.category_translation (
 product_category_name TEXT PRIMARY KEY, product_category_name_english TEXT
);

-- Recommended grain:
-- analytics.fact_sales = one row per order_item_id.
-- Do NOT aggregate raw order_items before joining orders/customers/products/sellers.
