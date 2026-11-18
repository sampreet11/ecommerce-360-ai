-- E-Commerce 360 AI Platform: physical schema (PostgreSQL; also loadable by SQLite for unit tests)
-- Source of truth for tables. Executed by Alembic migration 0001 and by the test suite.
-- Grain notes:
--   fact_sales        one row per order item (order_id, order_item_id)
--   customer_360      one row per customer_unique_id (delivered orders only)
--   cohort_retention  one row per (cohort_month, cohort_idx)
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS analytics.dim_seller (
  seller_id TEXT PRIMARY KEY, seller_zip_code_prefix INT, seller_city TEXT, seller_state TEXT);

CREATE TABLE IF NOT EXISTS analytics.dim_product (
  product_id TEXT PRIMARY KEY, product_category_name TEXT, product_name_lenght INT,
  product_description_lenght INT, product_photos_qty INT, product_weight_g NUMERIC,
  product_length_cm NUMERIC, product_height_cm NUMERIC, product_width_cm NUMERIC,
  product_category_name_english TEXT, category TEXT);

CREATE TABLE IF NOT EXISTS analytics.dim_date (
  date_key DATE PRIMARY KEY, year INT, quarter TEXT, month_number INT,
  month_name TEXT, year_month TEXT, week_number INT);

CREATE TABLE IF NOT EXISTS analytics.fact_sales (
  order_id TEXT NOT NULL, order_item_id INT NOT NULL, customer_id TEXT, customer_unique_id TEXT,
  product_id TEXT, seller_id TEXT, order_status TEXT, order_purchase_timestamp TIMESTAMP,
  price NUMERIC(12,2), freight_value NUMERIC(12,2), sales NUMERIC(12,2), gross_order_value NUMERIC(12,2),
  category TEXT, customer_state TEXT, seller_state TEXT,
  delivery_days NUMERIC, late_days NUMERIC, late_flag SMALLINT, purchase_month DATE,
  PRIMARY KEY (order_id, order_item_id));
CREATE INDEX IF NOT EXISTS ix_fact_month ON analytics.fact_sales(purchase_month);
CREATE INDEX IF NOT EXISTS ix_fact_customer ON analytics.fact_sales(customer_unique_id);
CREATE INDEX IF NOT EXISTS ix_fact_category ON analytics.fact_sales(category);
CREATE INDEX IF NOT EXISTS ix_fact_status ON analytics.fact_sales(order_status);
CREATE INDEX IF NOT EXISTS ix_fact_seller ON analytics.fact_sales(seller_id);
CREATE INDEX IF NOT EXISTS ix_fact_cust_state ON analytics.fact_sales(customer_state);

CREATE TABLE IF NOT EXISTS analytics.customer_360 (
  customer_unique_id TEXT PRIMARY KEY, first_purchase TIMESTAMP, last_purchase TIMESTAMP,
  orders INT, items INT, revenue NUMERIC(14,2), freight NUMERIC(14,2), recency_days INT, aov NUMERIC(14,2),
  repeat_flag SMALLINT, cohort_month DATE, r_score INT, f_score INT, m_score INT, rfm_score INT,
  rfm_segment TEXT, lifecycle TEXT);
CREATE INDEX IF NOT EXISTS ix_c360_segment ON analytics.customer_360(rfm_segment);

CREATE TABLE IF NOT EXISTS analytics.cohort_retention (
  cohort_month DATE NOT NULL, cohort_idx INT NOT NULL, active_customers INT, cohort_size INT,
  retention NUMERIC, PRIMARY KEY (cohort_month, cohort_idx));

CREATE TABLE IF NOT EXISTS analytics.market_basket_pairs (
  category_a TEXT NOT NULL, category_b TEXT NOT NULL, orders_together INT, support NUMERIC,
  PRIMARY KEY (category_a, category_b));

-- Conversation memory
CREATE TABLE IF NOT EXISTS app.chat_messages (
  id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
  metadata_json TEXT, created_at TIMESTAMP NOT NULL);
CREATE INDEX IF NOT EXISTS ix_chat_session ON app.chat_messages(session_id, created_at);

-- Audit of AI-generated SQL (no secrets stored)
CREATE TABLE IF NOT EXISTS app.query_log (
  id TEXT PRIMARY KEY, session_id TEXT, question TEXT, generated_sql TEXT, executed_sql TEXT,
  status TEXT, rejection_reason TEXT, row_count INT, duration_ms INT, mode TEXT, created_at TIMESTAMP NOT NULL);
