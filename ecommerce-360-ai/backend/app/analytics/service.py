"""Deterministic analytics layer: every number the UI (and the offline chatbot) shows comes from here.

Metric definitions
  revenue  = SUM(sales)  (item price, excl. freight). NOT profit.
  orders   = distinct order_id; delivery metrics are ORDER grain (one row per order via v_order_level)
  late %   = late orders / delivered orders that have a delivery date
  Default scope: delivered orders.
"""
from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ..database.executor import Executor

FORECAST_LAST_COMPLETE_MONTH = date(2018, 8, 1)  # final Olist month is partial (matches Python/analysis_and_forecasting.py)
SORTABLE_CATEGORY = {"revenue", "orders", "items", "aov", "customers", "freight"}


def clean(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10] if isinstance(v, date) and not isinstance(v, datetime) else v.isoformat(sep=" ")[:19]
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def rows(rs: list[dict]) -> list[dict]:
    return [{k: clean(v) for k, v in r.items()} for r in rs]


def _range(col: str, start: date | None, end: date | None) -> tuple[str, dict]:
    sql, p = "", {}
    if start:
        sql += f" AND {col} >= :start"; p["start"] = start
    if end:
        sql += f" AND {col} <= :end"; p["end"] = end
    return sql, p


def _div(a, b):
    return (a / b) if (a is not None and b) else None


class Analytics:
    def __init__(self, ex: Executor):
        self.ex = ex

    # ---------- system ----------
    def coverage(self) -> dict:
        r = self.ex.query("SELECT MIN(purchase_month) AS first_month, MAX(purchase_month) AS last_month, "
                          "COUNT(DISTINCT order_id) AS orders, COUNT(*) AS items FROM analytics.fact_sales")[0]
        return rows([r])[0]

    def table_counts(self) -> dict[str, int]:
        out = {}
        for t in ("fact_sales", "customer_360", "dim_product", "dim_seller", "dim_date",
                  "cohort_retention", "market_basket_pairs"):
            out[t] = int(self.ex.query(f"SELECT COUNT(*) AS n FROM analytics.{t}")[0]["n"])
        return out

    # ---------- dashboard ----------
    def overview(self, start=None, end=None) -> dict:
        rng, p = _range("purchase_month", start, end)
        r = rows(self.ex.query(
            "SELECT COUNT(*) AS orders, COUNT(DISTINCT customer_unique_id) AS customers, SUM(revenue) AS revenue, "
            "SUM(freight) AS freight, SUM(items) AS items, AVG(delivery_days) AS avg_delivery_days, "
            "SUM(CASE WHEN delivery_days IS NOT NULL THEN late_flag ELSE 0 END) AS late_orders, "
            "SUM(CASE WHEN delivery_days IS NOT NULL THEN 1 ELSE 0 END) AS orders_with_delivery_date "
            f"FROM analytics.v_order_level WHERE order_status = 'delivered'{rng}", p))[0]
        r["revenue"] = r["revenue"] or 0.0
        r["aov"] = _div(r["revenue"], r["orders"])
        r["late_delivery_pct"] = (_div(r["late_orders"], r["orders_with_delivery_date"]) or 0) * 100 if r["orders_with_delivery_date"] else None
        r["freight_pct_of_revenue"] = (_div(r["freight"], r["revenue"]) or 0) * 100 if r["revenue"] else None
        cm = self.customer_metrics(start, end)
        r["repeat_customer_pct"] = cm["repeat_customer_pct"]
        r["status_distribution"] = self.status_distribution(start, end)
        r["review_score_available"] = False
        return r

    def status_distribution(self, start=None, end=None) -> list[dict]:
        rng, p = _range("purchase_month", start, end)
        return rows(self.ex.query(
            "SELECT order_status, COUNT(*) AS orders, SUM(revenue) AS revenue FROM analytics.v_order_level "
            f"WHERE 1=1{rng} GROUP BY order_status ORDER BY orders DESC", p))

    def revenue_trend(self, start=None, end=None) -> list[dict]:
        rng, p = _range("purchase_month", start, end)
        data = rows(self.ex.query(
            "SELECT purchase_month AS month, revenue, freight, items, orders, customers, aov "
            f"FROM analytics.v_monthly_kpis WHERE 1=1{rng} ORDER BY purchase_month", p))
        prev = None
        for d in data:
            d["mom_growth_pct"] = ((d["revenue"] - prev) / prev * 100) if prev else None
            prev = d["revenue"]
        return data

    def top_categories(self, start=None, end=None, limit=10, sort="revenue", page=1, page_size=None) -> dict:
        if sort not in SORTABLE_CATEGORY:
            sort = "revenue"
        rng, p = _range("purchase_month", start, end)
        allrows = rows(self.ex.query(
            "SELECT category, SUM(sales) AS revenue, SUM(freight_value) AS freight, COUNT(*) AS items, "
            "COUNT(DISTINCT order_id) AS orders, COUNT(DISTINCT customer_unique_id) AS customers, "
            "SUM(sales) * 1.0 / NULLIF(COUNT(DISTINCT order_id), 0) AS aov "
            f"FROM analytics.fact_sales WHERE order_status = 'delivered'{rng} GROUP BY category", p))
        total = sum(r["revenue"] or 0 for r in allrows)
        allrows.sort(key=lambda r: (r[sort] is None, -(r[sort] or 0)))
        cum = 0.0
        for r in allrows:
            r["share_pct"] = _div(r["revenue"], total) * 100 if total else None
        for r in sorted(allrows, key=lambda r: -(r["revenue"] or 0)):
            cum += r["share_pct"] or 0
            r["cumulative_share_pct"] = cum
        size = page_size or limit
        start_i = (page - 1) * size
        return {"total_revenue": total, "category_count": len(allrows), "page": page, "page_size": size,
                "items": allrows[start_i:start_i + size]}

    def delivery_performance(self, start=None, end=None, min_orders=250) -> dict:
        rng, p = _range("purchase_month", start, end)
        base = f"FROM analytics.v_order_level WHERE order_status = 'delivered' AND delivery_days IS NOT NULL{rng}"
        o = rows(self.ex.query(f"SELECT COUNT(*) AS orders, AVG(delivery_days) AS avg_delivery_days, "
                               f"SUM(late_flag) AS late_orders {base}", p))[0]
        o["late_delivery_pct"] = (_div(o["late_orders"], o["orders"]) or 0) * 100 if o["orders"] else None
        buckets = rows(self.ex.query(
            "SELECT CASE WHEN delivery_days <= 7 THEN '0-7 days' WHEN delivery_days <= 14 THEN '8-14 days' "
            "WHEN delivery_days <= 21 THEN '15-21 days' WHEN delivery_days <= 30 THEN '22-30 days' "
            f"ELSE '31+ days' END AS bucket, COUNT(*) AS orders {base} GROUP BY 1", p))
        order = ["0-7 days", "8-14 days", "15-21 days", "22-30 days", "31+ days"]
        buckets.sort(key=lambda b: order.index(b["bucket"]))
        monthly = rows(self.ex.query(
            f"SELECT purchase_month AS month, COUNT(*) AS orders, AVG(delivery_days) AS avg_delivery_days, "
            f"AVG(late_flag * 1.0) * 100 AS late_pct {base} GROUP BY purchase_month ORDER BY purchase_month", p))
        sp = dict(p); sp["min_orders"] = min_orders
        states = rows(self.ex.query(
            f"SELECT customer_state AS state, COUNT(*) AS orders, AVG(delivery_days) AS avg_delivery_days, "
            f"SUM(late_flag) AS late_orders, AVG(late_flag * 1.0) * 100 AS late_pct {base} "
            f"GROUP BY customer_state HAVING COUNT(*) >= :min_orders ORDER BY late_pct DESC", sp))
        return {"overall": o, "distribution": buckets, "monthly": monthly, "by_state": states,
                "min_orders_per_state": min_orders}

    def customer_metrics(self, start=None, end=None) -> dict:
        rng, p = _range("purchase_month", start, end)
        r = rows(self.ex.query(
            "SELECT COUNT(*) AS customers, SUM(CASE WHEN n > 1 THEN 1 ELSE 0 END) AS repeat_customers, "
            "SUM(rev) AS revenue, SUM(CASE WHEN n > 1 THEN rev ELSE 0 END) AS repeat_revenue FROM ("
            "SELECT customer_unique_id, COUNT(*) AS n, SUM(revenue) AS rev FROM analytics.v_order_level "
            f"WHERE order_status = 'delivered'{rng} GROUP BY customer_unique_id) t", p))[0]
        c = r["customers"] or 0
        dist = rows(self.ex.query(
            "SELECT CASE WHEN n >= 4 THEN '4+' ELSE CAST(n AS TEXT) END AS orders_per_customer, COUNT(*) AS customers FROM ("
            "SELECT customer_unique_id, COUNT(*) AS n FROM analytics.v_order_level "
            f"WHERE order_status = 'delivered'{rng} GROUP BY customer_unique_id) t GROUP BY 1 ORDER BY 1", p))
        return {"customers": c, "repeat_customers": r["repeat_customers"] or 0,
                "repeat_customer_pct": (_div(r["repeat_customers"] or 0, c) or 0) * 100 if c else None,
                "repeat_revenue_share_pct": (_div(r["repeat_revenue"] or 0, r["revenue"]) or 0) * 100 if r["revenue"] else None,
                "orders_per_customer": dist}

    def review_analysis(self) -> dict:
        return {"available": False,
                "reason": ("Review scores are not part of the processed dataset in this project (no order_reviews table "
                           "was included). Import olist_order_reviews_dataset.csv and extend the schema to enable "
                           "review analysis."),
                "delivery_proxy": "Late-delivery rate by state is available under /api/dashboard/delivery-performance."}

    # ---------- analytics pages ----------
    def sales(self, start=None, end=None) -> dict:
        rng, p = _range("purchase_month", start, end)
        buckets = rows(self.ex.query(
            "SELECT CASE WHEN revenue < 50 THEN '< 50' WHEN revenue < 100 THEN '50-99' WHEN revenue < 200 THEN '100-199' "
            "WHEN revenue < 500 THEN '200-499' ELSE '500+' END AS bucket, COUNT(*) AS orders "
            f"FROM analytics.v_order_level WHERE order_status = 'delivered'{rng} GROUP BY 1", p))
        order = ["< 50", "50-99", "100-199", "200-499", "500+"]
        buckets.sort(key=lambda b: order.index(b["bucket"]))
        states = rows(self.ex.query(
            "SELECT customer_state AS state, SUM(revenue) AS revenue, COUNT(*) AS orders FROM analytics.v_order_level "
            f"WHERE order_status = 'delivered'{rng} GROUP BY customer_state ORDER BY revenue DESC LIMIT 10", p))
        return {"monthly": self.revenue_trend(start, end), "categories": self.top_categories(start, end, limit=15)["items"],
                "order_value_distribution": buckets, "top_states": states, "overview": self.overview(start, end)}

    def customers(self) -> dict:
        seg = rows(self.ex.query("SELECT rfm_segment, customers, revenue, avg_orders, avg_recency_days, "
                                 "avg_revenue_per_customer FROM analytics.v_rfm_segments ORDER BY revenue DESC"))
        total_rev = sum(s["revenue"] or 0 for s in seg)
        for s in seg:
            s["revenue_share_pct"] = _div(s["revenue"], total_rev) * 100 if total_rev else None
        life = rows(self.ex.query("SELECT lifecycle, customers, historical_revenue FROM analytics.v_lifecycle "
                                  "ORDER BY historical_revenue DESC"))
        nr = rows(self.ex.query(
            "SELECT CASE WHEN repeat_flag = 1 THEN 'Repeat' ELSE 'One-time' END AS customer_type, COUNT(*) AS customers, "
            "SUM(revenue) AS revenue, AVG(aov * 1.0) AS avg_order_value FROM analytics.customer_360 GROUP BY 1"))
        return {"rfm_segments": seg, "lifecycle": life, "new_vs_repeat": nr,
                "metrics": self.customer_metrics(),
                "notes": ["Lifecycle buckets measure time since last purchase vs the dataset's last date "
                          "(2018 snapshot); they are not subscription churn."]}

    def products(self, sort="revenue", page=1, page_size=15, start=None, end=None) -> dict:
        cats = self.top_categories(start, end, sort=sort, page=page, page_size=page_size)
        rng, p = _range("f.purchase_month", start, end)
        top = rows(self.ex.query(
            "SELECT f.product_id, f.category, SUM(f.sales) AS revenue, COUNT(*) AS items, COUNT(DISTINCT f.order_id) AS orders "
            f"FROM analytics.fact_sales f WHERE f.order_status = 'delivered'{rng} GROUP BY f.product_id, f.category "
            "ORDER BY revenue DESC LIMIT 15", p))
        basket = rows(self.ex.query("SELECT category_a, category_b, orders_together, support FROM analytics.market_basket_pairs "
                                    "ORDER BY orders_together DESC LIMIT 15"))
        return {"categories": cats, "top_products": top, "market_basket": basket,
                "review_analysis": self.review_analysis()}

    def operations(self, start=None, end=None, min_seller_orders=30, page=1, page_size=15) -> dict:
        sellers_all = rows(self.ex.query(
            "SELECT seller_id, seller_state, orders, revenue, avg_delivery_days, late_orders, late_rate * 100 AS late_pct "
            "FROM analytics.v_seller_performance WHERE orders >= :m ORDER BY late_rate DESC, orders DESC",
            {"m": min_seller_orders}))
        i = (page - 1) * page_size
        return {"delivery": self.delivery_performance(start, end), "sellers": sellers_all[i:i + page_size],
                "sellers_total": len(sellers_all), "min_seller_orders": min_seller_orders, "page": page,
                "page_size": page_size, "review_analysis": self.review_analysis()}

    def retention(self, max_idx=12) -> dict:
        data = rows(self.ex.query("SELECT cohort_month, cohort_idx, active_customers, cohort_size, retention "
                                  "FROM analytics.cohort_retention ORDER BY cohort_month, cohort_idx"))
        if not data:
            return {"matrix": [], "curve": []}
        def midx(s): y, m = int(s[:4]), int(s[5:7]); return y * 12 + m
        last = max(midx(d["cohort_month"]) + d["cohort_idx"] for d in data)
        sizes = {d["cohort_month"]: d["cohort_size"] for d in data}
        matrix = {}
        for d in data:
            if d["cohort_idx"] <= max_idx:
                matrix.setdefault(d["cohort_month"], {"cohort_month": d["cohort_month"], "cohort_size": d["cohort_size"], "retention": {}})["retention"][d["cohort_idx"]] = round(d["retention"] * 100, 2)
        curve = []
        for k in range(0, max_idx + 1):
            obs = [c for c in sizes if midx(c) + k <= last]
            denom = sum(sizes[c] for c in obs)
            num = sum(d["active_customers"] for d in data if d["cohort_idx"] == k and d["cohort_month"] in obs)
            curve.append({"months_since_first_purchase": k, "retention_pct": _div(num, denom) * 100 if denom else None,
                          "cohorts_observed": len(obs)})
        return {"matrix": list(matrix.values()), "curve": curve,
                "note": "Retention = share of a cohort that placed another delivered order k months after first purchase. "
                        "This is repeat-purchase behaviour, not subscription retention."}

    def forecast(self, horizon=6, window=3) -> dict:
        hist = rows(self.ex.query("SELECT purchase_month AS month, revenue FROM analytics.v_monthly_kpis "
                                  "WHERE purchase_month <= :cut ORDER BY purchase_month",
                                  {"cut": FORECAST_LAST_COMPLETE_MONTH}))
        vals = [h["revenue"] for h in hist]
        out, y, m = [], int(hist[-1]["month"][:4]), int(hist[-1]["month"][5:7])
        for _ in range(horizon):
            v = sum(vals[-window:]) / window
            vals.append(v)
            m += 1
            if m > 12: m, y = 1, y + 1
            out.append({"month": f"{y:04d}-{m:02d}-01", "forecast_revenue": v})
        return {"history": hist, "forecast": out, "method": f"{window}-month rolling-mean baseline, recursive",
                "disclaimer": "Directional baseline only; not a trained ML model and not a guaranteed outcome. "
                              "Data ends in 2018, so the forecast is for illustration."}
