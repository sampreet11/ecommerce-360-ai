"""Business summary report: JSON dict -> CSV / Markdown / PDF. All figures come from the Analytics layer."""
from __future__ import annotations

import csv
import io
from datetime import date

from ..analytics.insights import build_insights
from ..analytics.service import Analytics


def build_summary(a: Analytics, start: date | None = None, end: date | None = None, cur: str = "R$") -> dict:
    ov = a.overview(start, end)
    cats = a.top_categories(start, end, limit=10)
    dp = a.delivery_performance(start, end)
    cov = a.coverage()
    return {
        "title": "E-Commerce 360° Executive Summary",
        "period": {"start": str(start or cov["first_month"]), "end": str(end or cov["last_month"]),
                   "note": "Historical Olist data (Sep 2016 - Sep 2018); the final month is partial. Not live data."},
        "currency": cur,
        "kpis": {k: ov[k] for k in ("revenue", "orders", "customers", "aov", "avg_delivery_days", "late_delivery_pct",
                                    "repeat_customer_pct", "freight", "items")},
        "top_categories": cats["items"][:10],
        "worst_states_by_late_rate": dp["by_state"][:5],
        "monthly_revenue": a.revenue_trend(start, end),
        "insights": build_insights(a, start, end, cur),
        "definitions": [
            "Revenue = sum of item price on delivered orders (excludes freight). It is not profit: no cost data exists.",
            "Orders = distinct order_id. Late % = late delivered orders / delivered orders with a delivery date.",
            "Repeat customer = more than one delivered order (repeat purchasing, not subscription churn).",
            "Review scores are not part of the loaded dataset and are not reported."],
    }


def to_csv(s: dict) -> bytes:
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow([s["title"]]); w.writerow(["period", s["period"]["start"], s["period"]["end"]]); w.writerow(["currency", s["currency"]])
    w.writerow([]); w.writerow(["KPI", "value"])
    for k, v in s["kpis"].items():
        w.writerow([k, v])
    w.writerow([]); w.writerow(["category", "revenue", "orders", "aov", "share_pct"])
    for c in s["top_categories"]:
        w.writerow([c["category"], c["revenue"], c["orders"], c["aov"], c["share_pct"]])
    w.writerow([]); w.writerow(["month", "revenue", "orders", "customers", "aov"])
    for m in s["monthly_revenue"]:
        w.writerow([m["month"], m["revenue"], m["orders"], m["customers"], m["aov"]])
    return buf.getvalue().encode("utf-8-sig")


def _fmt(k, v, cur):
    if v is None: return "n/a"
    if k in ("revenue", "aov", "freight"): return f"{cur}{v:,.2f}"
    if k.endswith("_pct"): return f"{v:.2f}%"
    if k == "avg_delivery_days": return f"{v:.2f} days"
    return f"{v:,.0f}" if isinstance(v, (int, float)) else str(v)


def to_markdown(s: dict, narrative: str | None = None) -> bytes:
    c = s["currency"]; L = [f"# {s['title']}", f"*Period: {s['period']['start']} to {s['period']['end']}. {s['period']['note']}*", ""]
    if narrative: L += ["## Executive narrative", narrative, ""]
    L += ["## KPIs", *[f"- **{k.replace('_', ' ')}:** {_fmt(k, v, c)}" for k, v in s["kpis"].items()], "", "## Top categories"]
    L += [f"{i+1}. {x['category']}: {c}{x['revenue']:,.2f} ({x['share_pct']:.1f}%)" for i, x in enumerate(s["top_categories"])]
    L += ["", "## Insights"] + [f"- [{i['type']}] **{i['title']}** - {i['text']} _(basis: {i['basis']})_" for i in s["insights"]]
    L += ["", "## Definitions"] + [f"- {d}" for d in s["definitions"]]
    return "\n".join(L).encode("utf-8")


def to_pdf(s: dict, narrative: str | None = None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape as esc
    c, st, buf = s["currency"], getSampleStyleSheet(), io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=s["title"], leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    P = lambda t, style="BodyText": Paragraph(esc(t), st[style])
    story = [P(s["title"], "Title"), P(f"Period: {s['period']['start']} to {s['period']['end']}. {s['period']['note']}", "Italic"), Spacer(1, 10)]
    if narrative:
        story += [P("Executive narrative", "Heading2"), P(narrative), Spacer(1, 8)]
    def table(data, widths=None):
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")), ("FONTSIZE", (0, 0), (-1, -1), 9),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")])]))
        return t
    story += [P("Key metrics", "Heading2"), table([["Metric", "Value"]] + [[k.replace("_", " "), _fmt(k, v, c)] for k, v in s["kpis"].items()], [250, 250]), Spacer(1, 10)]
    story += [P("Top categories by revenue", "Heading2"), table([["#", "Category", "Revenue", "Orders", "Share"]] +
              [[i + 1, x["category"], f"{c}{x['revenue']:,.0f}", f"{x['orders']:,}", f"{x['share_pct']:.1f}%"] for i, x in enumerate(s["top_categories"])]), Spacer(1, 10)]
    story += [P("Insights", "Heading2")]
    for i in s["insights"]:
        story.append(P(f"[{i['type']}] {i['title']}: {i['text']} (basis: {i['basis']})"))
    story += [Spacer(1, 8), P("Definitions & limitations", "Heading2")] + [P("- " + d) for d in s["definitions"]]
    doc.build(story)
    return buf.getvalue()
