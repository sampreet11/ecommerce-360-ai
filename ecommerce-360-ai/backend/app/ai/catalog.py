"""The ONLY relations and columns the AI may query. Also the schema text given to the LLM."""
from __future__ import annotations

ALLOWED: dict[str, dict] = {
    "v_order_level": {
        "desc": "ONE ROW PER ORDER (all statuses). Use for order counts, delivery time and late rate.",
        "cols": {"order_id": "text", "customer_unique_id": "text", "customer_state": "text (UF)",
                 "order_status": "delivered/shipped/canceled/invoiced/processing/unavailable/approved",
                 "purchase_ts": "timestamp", "purchase_month": "date (first day of month)",
                 "items": "items in order", "revenue": "sum of item price (excl. freight)",
                 "freight": "sum freight", "delivery_days": "days purchase->delivery, NULL if undelivered",
                 "late_flag": "1 if delivered after estimated date else 0"}},
    "v_monthly_kpis": {
        "desc": "Delivered orders per purchase month.",
        "cols": {"purchase_month": "date", "revenue": "numeric", "freight": "numeric", "items": "int",
                 "orders": "int", "customers": "int", "aov": "revenue per order"}},
    "v_category_kpis": {
        "desc": "Delivered orders per product category (English names, e.g. bed_bath_table).",
        "cols": {"category": "text", "revenue": "numeric", "freight": "numeric", "items": "int",
                 "orders": "int", "customers": "int", "aov": "numeric"}},
    "v_delivery_by_state": {
        "desc": "Delivery performance by customer state, delivered orders with a delivery date.",
        "cols": {"customer_state": "text", "orders": "int", "avg_delivery_days": "numeric",
                 "late_orders": "int", "late_rate": "0..1 fraction"}},
    "v_status_distribution": {
        "desc": "Orders and revenue by order status (all statuses).",
        "cols": {"order_status": "text", "orders": "int", "revenue": "numeric"}},
    "v_seller_performance": {
        "desc": "Per seller, delivered orders with delivery date.",
        "cols": {"seller_id": "text", "seller_state": "text", "orders": "int", "revenue": "numeric",
                 "avg_delivery_days": "numeric", "late_orders": "int", "late_rate": "0..1 fraction"}},
    "v_rfm_segments": {
        "desc": "RFM segment summary (customers with delivered orders).",
        "cols": {"rfm_segment": "text", "customers": "int", "revenue": "numeric", "avg_orders": "numeric",
                 "avg_recency_days": "numeric", "avg_revenue_per_customer": "numeric"}},
    "v_lifecycle": {
        "desc": "Customers by recency lifecycle bucket (lapsed >=180d etc.). Not subscription churn.",
        "cols": {"lifecycle": "text", "customers": "int", "historical_revenue": "numeric"}},
    "fact_sales": {
        "desc": "ONE ROW PER ORDER ITEM, all statuses. Revenue = SUM(sales). Count orders with COUNT(DISTINCT order_id).",
        "cols": {"order_id": "text", "order_item_id": "int", "customer_unique_id": "text", "product_id": "text",
                 "seller_id": "text", "order_status": "text", "order_purchase_timestamp": "timestamp",
                 "price": "numeric", "freight_value": "numeric", "sales": "numeric (=price)",
                 "gross_order_value": "price+freight", "category": "text", "customer_state": "text",
                 "seller_state": "text", "delivery_days": "numeric", "late_days": "numeric",
                 "late_flag": "0/1", "purchase_month": "date"}},
    "customer_360": {
        "desc": "ONE ROW PER CUSTOMER (customer_unique_id), delivered orders only.",
        "cols": {"customer_unique_id": "text", "first_purchase": "timestamp", "last_purchase": "timestamp",
                 "orders": "int", "items": "int", "revenue": "numeric", "freight": "numeric",
                 "recency_days": "days since last purchase vs 2018 snapshot", "aov": "numeric",
                 "repeat_flag": "1 if orders>1", "cohort_month": "date", "r_score": "1-5", "f_score": "1-5",
                 "m_score": "1-5", "rfm_score": "int", "rfm_segment": "text", "lifecycle": "text"}},
    "cohort_retention": {
        "desc": "Monthly acquisition cohorts; cohort_idx = months since first purchase.",
        "cols": {"cohort_month": "date", "cohort_idx": "int", "active_customers": "int",
                 "cohort_size": "int", "retention": "0..1 fraction"}},
    "market_basket_pairs": {
        "desc": "Category pairs bought in the same order.",
        "cols": {"category_a": "text", "category_b": "text", "orders_together": "int", "support": "fraction"}},
}

COLUMNS = {t: set(v["cols"]) for t, v in ALLOWED.items()}
SCHEMA = "analytics"


def schema_prompt() -> str:
    lines = []
    for t, v in ALLOWED.items():
        cols = ", ".join(f"{c} ({d})" for c, d in v["cols"].items())
        lines.append(f"- {t}: {v['desc']}\n    columns: {cols}")
    return "\n".join(lines)


METRIC_RULES = """\
Business definitions (follow exactly):
- Revenue / sales = SUM(sales) (item price, excluding freight). It is NOT profit; no cost data exists.
- Orders = COUNT(DISTINCT order_id). Items = COUNT(*) on fact_sales. Never COUNT(*) on fact_sales for orders.
- Default scope is delivered orders (order_status = 'delivered') unless the user asks about other statuses.
- Average order value = revenue / distinct orders.
- Avg delivery days and late rate use delivered orders with a non-NULL delivery_days at ORDER grain (v_order_level or v_delivery_by_state).
- Repeat customer = customer_360.repeat_flag = 1 (more than one delivered order). This is repeat purchasing, not subscription churn.
- Data covers 2016-09 to 2018-09 (the final month is partial). It is historical, not live.
- Currency is Brazilian real (R$).
- NOT AVAILABLE in the database: review scores, payments, product cost/profit/margin, discounts. If asked, answer intent "unsupported".
"""
