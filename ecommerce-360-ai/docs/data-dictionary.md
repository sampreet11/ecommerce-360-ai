# Data dictionary & KPI definitions

## What was actually in the ZIP
Processed, model-ready CSVs only: `fact_sales`, `customer_360`, `dim_seller`, `dim_product`, `dim_date`, `cohort_retention`,
`market_basket_category_pairs`, plus derived `monthly_kpis`, `category_kpis`, `revenue_forecast` (used for test reconciliation).
**Not included:** raw `orders`, `order_reviews`, `order_payments`, `geolocation`. Therefore review scores, payments and
delivered timestamps are not available; review analysis is reported as "unavailable" instead of being invented.

## Tables (schema `analytics`)
| Table | Grain | Rows loaded |
|---|---|---|
| fact_sales | one row per order item (order_id, order_item_id); all order statuses | 112,650 |
| customer_360 | one row per customer_unique_id (customers with a delivered order) | 93,358 |
| dim_product / dim_seller / dim_date | one row per product / seller / day | 32,951 / 3,095 / 774 |
| cohort_retention | (cohort_month, cohort_idx) | 219 |
| market_basket_pairs | category pair | 260 |
Chat memory lives in `app.chat_messages`; AI query audit in `app.query_log`.

## Views
`v_order_level` (one row per order; the key to avoiding double counting), `v_monthly_kpis`, `v_category_kpis`,
`v_delivery_by_state`, `v_status_distribution`, `v_seller_performance`, `v_rfm_segments`, `v_lifecycle`.

## KPI definitions (scope: delivered orders unless noted)
| KPI | Definition |
|---|---|
| Revenue | SUM(sales) = SUM(item price). Excludes freight. **Not profit** (no cost data). |
| Orders | COUNT(DISTINCT order_id) |
| Items | row count of fact_sales |
| Customers | COUNT(DISTINCT customer_unique_id) |
| AOV | Revenue / Orders |
| Avg delivery time | mean over orders with a delivery date of MAX(delivery_days) per order |
| Late delivery % | late orders / delivered orders with a delivery date |
| Repeat customer % | customers with >1 delivered order / customers (repeat purchasing, not churn) |
| RFM | scores from `customer_360` (snapshot = last purchase date in data, Sept 2018) |

## Reconciliation with the original README (important)
Original README: $13.59M sales, 2.9% repeat, 7.9% late. Recomputed here:
- 13,591,643.70 is SUM(sales) over **all** statuses; delivered-only revenue is **13,221,498.11**.
- Repeat rate over delivered customers is **3.00%** (2,801/93,358), not 2.9%.
- Late rate is **8.11%** (7,826/96,470) with delivery-date denominator, not 7.9%.
- README uses `$`; Olist amounts are Brazilian reais, so this app shows **R$**. The earlier prototype used `₹` (incorrect).
Verify these against the Power BI file; this app's numbers are reproducible by `backend/tests`.
