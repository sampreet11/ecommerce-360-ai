"""Offline (no API key) question understanding: keyword intents -> pre-approved SQL.

These SQL templates still pass through the same guard + read-only executor as LLM SQL.
This is NOT natural-language understanding; it covers a fixed set of common questions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
SAFE_ID = re.compile(r"^[a-z0-9_]+$")


@dataclass
class Plan:
    intent: str
    sql: str | None = None
    chart: dict | None = None
    calc: str = ""
    followups: list[str] = field(default_factory=list)
    narrate: Callable[[list[dict]], str] | None = None
    message: str | None = None          # used for no-SQL answers
    focus: dict | None = None            # entity remembered for follow-ups
    status: str = "ok"


def _n(q: str, default: int = 5, cap: int = 20) -> int:
    m = re.search(r"\b(?:top|best|highest|lowest|bottom|worst)\s+(\d+)\b|\b(\d+)\s+(?:top|best|categories|category)\b", q)
    if m:
        return max(1, min(cap, int(next(g for g in m.groups() if g))))
    for w, v in NUM_WORDS.items():
        if re.search(rf"\b{w}\b", q):
            return v
    return default


def money(v, cur="R$"): return f"{cur}{v:,.2f}"


def match(message: str, history: list[dict], cur: str = "R$") -> Plan | None:
    q = re.sub(r"\s+", " ", message.lower()).strip()
    has = lambda *ws: any(w in q for w in ws)

    # -- unsupported (honest refusals) ---------------------------------------------------------
    if has("profit", "margin", "cost of goods", "discount"):
        return Plan("unsupported", status="unsupported", message=(
            "I can't calculate profit, margin or discount impact: the Olist data has no product-cost or discount fields. "
            "I can show **revenue** (item price, excluding freight) and **freight** instead."),
            followups=["What is total revenue and freight?", "Which categories generate the most revenue?"])
    if has("review", "rating", "satisf", "nps", "payment", "installment"):
        return Plan("unsupported", status="unsupported", message=(
            "Review scores and payment data are not included in the processed dataset loaded into this platform, so I can't "
            "answer that. I can analyse delivery performance (late rate by state) as an operational proxy."),
            followups=["Identify our delivery problems.", "What percentage of orders were delivered late?"])

    # -- follow-up with memory ------------------------------------------------------------------
    focus = next((m["metadata"]["focus"] for m in reversed(history) if m.get("metadata") and m["metadata"].get("focus")), None)
    if focus and focus.get("category") and re.search(r"\b(it|that|this one|that category|this category)\b", q) \
            and has("how much", "revenue", "generate", "sales", "orders", "aov", "average"):
        cat = focus["category"]
        if SAFE_ID.match(cat):
            return Plan("followup_category", sql=(
                f"SELECT category, revenue, orders, items, aov FROM v_category_kpis WHERE category = '{cat}'"),
                calc=f"Revenue, orders and AOV for the category '{cat}' carried over from the previous answer.",
                narrate=lambda r: (f"'{r[0]['category']}' generated {money(r[0]['revenue'], cur)} from {r[0]['orders']:,} delivered orders "
                                   f"(AOV {money(r[0]['aov'], cur)})." if r else "No data."),
                followups=["Compare revenue across the top five categories."], focus=focus)

    # -- insights / recommendations / reports (non-SQL; use the analytics service) ---------------
    if has("recommend", "insight", "trend", "executive report", "summary", "summarise", "summarize", "action"):
        return Plan("insights")

    # -- revenue / orders -------------------------------------------------------------------------
    if has("categor") and has("lowest", "worst", "bottom", "least"):
        n = _n(q)
        return Plan("bottom_categories", sql=f"SELECT category, revenue, orders FROM v_category_kpis ORDER BY revenue ASC LIMIT {n}",
                    chart={"type": "bar", "x": "category", "y": "revenue"},
                    calc=f"Delivered-order revenue by category, lowest {n}.",
                    narrate=lambda r: "Lowest-revenue categories: " + "; ".join(f"{x['category']} ({money(x['revenue'], cur)})" for x in r) + ".",
                    followups=["Which categories are performing best?"])
    if has("categor", "compare revenue", "product line") :
        n = _n(q)
        def nar(r):
            tot = sum(x["revenue"] for x in r)
            lines = "; ".join(f"{i+1}. {x['category']} {money(x['revenue'], cur)}" for i, x in enumerate(r))
            return f"Top {len(r)} categories by delivered-order revenue: {lines}. Together they total {money(tot, cur)}."
        return Plan("top_categories", sql=f"SELECT category, revenue, orders, aov FROM v_category_kpis ORDER BY revenue DESC LIMIT {n}",
                    chart={"type": "bar", "x": "category", "y": "revenue"},
                    calc=f"SUM(item price) per category over delivered orders, ranked descending, top {n}. Revenue excludes freight and is not profit.",
                    narrate=nar, followups=["How much did it generate?", "Which categories have the lowest revenue?"],
                    focus=None)  # focus filled by analyst from first row
    if has("month") and has("highest", "best", "peak", "most"):
        return Plan("best_month", sql="SELECT purchase_month AS month, revenue, orders FROM v_monthly_kpis ORDER BY revenue DESC LIMIT 3",
                    calc="Delivered-order revenue by purchase month, highest first.",
                    narrate=lambda r: f"The highest-revenue month was {r[0]['month'][:7]} with {money(r[0]['revenue'], cur)} from {r[0]['orders']:,} orders.",
                    followups=["Show monthly revenue."])
    if has("monthly", "per month", "by month", "over time"):
        return Plan("monthly", sql="SELECT purchase_month AS month, revenue, orders FROM v_monthly_kpis ORDER BY purchase_month",
                    chart={"type": "line", "x": "month", "y": "revenue"}, calc="Delivered-order revenue by purchase month.",
                    narrate=lambda r: f"Monthly revenue runs from {money(r[0]['revenue'], cur)} in {r[0]['month'][:7]} to {money(r[-1]['revenue'], cur)} in {r[-1]['month'][:7]} ({len(r)} months).",
                    followups=["Which month had the highest sales?"])
    if has("average order", "aov", "order value"):
        return Plan("aov", sql="SELECT SUM(revenue) AS revenue, SUM(orders) AS orders, SUM(revenue) * 1.0 / SUM(orders) AS aov FROM v_monthly_kpis",
                    calc="AOV = delivered revenue / distinct delivered orders (freight excluded).",
                    narrate=lambda r: f"Average order value is {money(r[0]['aov'], cur)} ({money(r[0]['revenue'], cur)} over {r[0]['orders']:,} delivered orders).",
                    followups=["What is total revenue?"])
    if has("late", "delay", "on time", "on-time"):
        if has("state", "region", "where", "problem"):
            pass  # handled below
        else:
            return Plan("late_rate", sql=("SELECT SUM(late_orders) AS late_orders, SUM(orders) AS orders, "
                                          "SUM(late_orders) * 100.0 / SUM(orders) AS late_pct FROM v_delivery_by_state"),
                        calc="Late orders / delivered orders with a delivery date (order grain).",
                        narrate=lambda r: f"{r[0]['late_orders']:,} of {r[0]['orders']:,} delivered orders ({r[0]['late_pct']:.2f}%) arrived after the estimated date.",
                        followups=["Identify our delivery problems."])
    if has("delivery") and has("problem", "state", "region", "worst", "slow", "identify", "performance"):
        return Plan("delivery_by_state", sql=("SELECT customer_state AS state, orders, avg_delivery_days, late_rate * 100 AS late_pct "
                                              "FROM v_delivery_by_state WHERE orders >= 250 ORDER BY late_rate DESC LIMIT 10"),
                    chart={"type": "bar", "x": "state", "y": "late_pct"},
                    calc="Late-order percentage by customer state (states with at least 250 delivered orders), worst first.",
                    narrate=lambda r: "Highest late-delivery rates: " + "; ".join(f"{x['state']} {x['late_pct']:.1f}% ({x['avg_delivery_days']:.1f} days avg)" for x in r[:5]) + ".",
                    followups=["What percentage of orders were delivered late?"])
    if has("delivery time", "delivery days", "how long"):
        return Plan("avg_delivery", sql="SELECT SUM(orders) AS orders, SUM(avg_delivery_days * orders) / SUM(orders) AS avg_days FROM v_delivery_by_state",
                    calc="Order-weighted average of state averages = average over delivered orders with a delivery date.",
                    narrate=lambda r: f"Average delivery time is {r[0]['avg_days']:.2f} days across {r[0]['orders']:,} delivered orders.")
    if has("repeat", "returning", "purchased more than once", "loyal"):
        return Plan("repeat", sql=("SELECT COUNT(*) AS customers, SUM(repeat_flag) AS repeat_customers, SUM(repeat_flag) * 100.0 / COUNT(*) AS repeat_pct, "
                                   "SUM(CASE WHEN repeat_flag = 1 THEN revenue ELSE 0 END) * 100.0 / SUM(revenue) AS repeat_revenue_share_pct FROM customer_360"),
                    calc="Customers with more than one delivered order / all customers with a delivered order. Repeat purchasing, not subscription churn.",
                    narrate=lambda r: (f"{r[0]['repeat_customers']:,} of {r[0]['customers']:,} customers ({r[0]['repeat_pct']:.2f}%) bought more than once; "
                                       f"they account for {r[0]['repeat_revenue_share_pct']:.1f}% of customer revenue."),
                    followups=["Show RFM segments.", "Give me three important business recommendations."])
    if has("rfm", "segment"):
        return Plan("rfm", sql="SELECT rfm_segment, customers, revenue FROM v_rfm_segments ORDER BY revenue DESC",
                    chart={"type": "bar", "x": "rfm_segment", "y": "revenue"}, calc="RFM segments from customer_360 (snapshot = last purchase date in data).",
                    narrate=lambda r: "Revenue by RFM segment: " + "; ".join(f"{x['rfm_segment']} {money(x['revenue'], cur)} ({x['customers']:,} customers)" for x in r) + ".")
    if has("status", "cancel"):
        return Plan("status", sql="SELECT order_status, orders, revenue FROM v_status_distribution ORDER BY orders DESC",
                    chart={"type": "bar", "x": "order_status", "y": "orders"}, calc="Orders by status (all statuses).",
                    narrate=lambda r: "Orders by status: " + "; ".join(f"{x['order_status']} {x['orders']:,}" for x in r) + ".")
    if has("customer") and has("how many", "number", "count", "total"):
        return Plan("customers", sql="SELECT COUNT(*) AS customers FROM customer_360",
                    calc="Distinct customer_unique_id with at least one delivered order.",
                    narrate=lambda r: f"There are {r[0]['customers']:,} unique customers with at least one delivered order.")
    if has("order") and has("how many", "number", "count", "total"):
        return Plan("orders", sql="SELECT SUM(orders) AS orders, SUM(items) AS items FROM v_monthly_kpis",
                    calc="Distinct delivered orders (order grain); items counted separately.",
                    narrate=lambda r: f"There are {r[0]['orders']:,} delivered orders containing {r[0]['items']:,} items.")
    if has("revenue", "sales", "gmv", "overall"):
        return Plan("total_revenue", sql="SELECT SUM(revenue) AS revenue, SUM(freight) AS freight, SUM(orders) AS orders, SUM(revenue) * 1.0 / SUM(orders) AS aov FROM v_monthly_kpis",
                    calc="SUM of item price over delivered orders (freight shown separately). Revenue is not profit.",
                    narrate=lambda r: (f"Total delivered-order revenue is {money(r[0]['revenue'], cur)} from {r[0]['orders']:,} orders "
                                       f"(AOV {money(r[0]['aov'], cur)}); freight adds {money(r[0]['freight'], cur)}."),
                    followups=["Which categories are performing best?", "Show monthly revenue."])
    return None


HELP = ("I'm running in **offline mode** (no OpenAI key configured), so I can answer a fixed set of questions: total revenue, "
        "orders/customers, average order value, top/bottom categories, best month, monthly trend, late-delivery rate, delivery "
        "problems by state, repeat customers, RFM segments, order status, and business recommendations. "
        "Add `OPENAI_API_KEY` to `.env` for open-ended questions.")
