"""Rule-based insights computed from real query results. Every insight carries its `basis`."""
from __future__ import annotations

from .service import Analytics


def build_insights(a: Analytics, start=None, end=None, cur="R$") -> list[dict]:
    ov = a.overview(start, end)
    cats = a.top_categories(start, end, limit=50)
    out: list[dict] = []
    items = cats["items"]
    if items:
        top5 = sum(c["share_pct"] or 0 for c in items[:5])
        out.append({"type": "observation", "title": "Revenue concentration",
                    "text": f"The top 5 of {cats['category_count']} categories generate {top5:.1f}% of revenue; "
                            f"'{items[0]['category']}' alone is {items[0]['share_pct']:.1f}%.",
                    "basis": "fact_sales, delivered orders, SUM(sales) by category"})
    if ov["repeat_customer_pct"] is not None:
        out.append({"type": "observation", "title": "Low repeat purchasing",
                    "text": f"{ov['repeat_customer_pct']:.1f}% of customers placed more than one delivered order.",
                    "basis": "v_order_level, delivered orders per customer_unique_id"})
        out.append({"type": "recommendation", "title": "Retention programme",
                    "text": "Test post-purchase email/cross-sell offers on one-time buyers; measure the lift in repeat rate "
                            "against a holdout group.", "basis": "Repeat-customer rate above (repeat purchasing, not churn)"})
    dp = a.delivery_performance(start, end)
    if dp["overall"]["late_delivery_pct"] is not None:
        out.append({"type": "observation", "title": "Delivery reliability",
                    "text": f"{dp['overall']['late_delivery_pct']:.1f}% of delivered orders arrived after the estimated date; "
                            f"average delivery time is {dp['overall']['avg_delivery_days']:.1f} days.",
                    "basis": "v_order_level, delivered orders with a delivery date"})
        if dp["by_state"]:
            w = dp["by_state"][0]
            out.append({"type": "recommendation", "title": "Target the slowest region",
                        "text": f"State {w['state']} has the highest late rate ({w['late_pct']:.1f}% over {w['orders']:,} orders); "
                                "review carriers and estimated-date promises there.",
                        "basis": f"v_order_level by customer_state (states with >= {dp['min_orders_per_state']} orders)"})
    tr = a.revenue_trend(start, end)
    if len(tr) >= 2:
        out.append({"type": "observation", "title": "Latest month vs previous",
                    "text": f"Revenue in {tr[-1]['month'][:7]} was {cur}{tr[-1]['revenue']:,.0f}"
                            + (f" ({tr[-1]['mom_growth_pct']:+.1f}% vs {tr[-2]['month'][:7]})." if tr[-1]['mom_growth_pct'] is not None else "."),
                    "basis": "v_monthly_kpis"})
    return out
