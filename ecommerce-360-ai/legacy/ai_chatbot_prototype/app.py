from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data" / "processed"
FACT_PATH = DATA_DIR / "fact_sales.csv"

app = FastAPI(title="E-Commerce 360 AI Chatbot", version="0.1.0",
              description="A local, data-grounded analytics chatbot prototype.")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


def load_fact() -> pd.DataFrame:
    if not FACT_PATH.exists():
        raise FileNotFoundError(f"Could not find analytics data: {FACT_PATH}")
    df = pd.read_csv(FACT_PATH)
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"], errors="coerce")
    for col in ("sales", "freight_value", "delivery_days", "late_flag"):
        if col in df:
            if col == "late_flag":
                df[col] = df[col].astype(str).str.lower().isin(["true", "1", "yes"])
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def money(v: float) -> str:
    return f"₹{v:,.2f}"


def reply(message: str, df: pd.DataFrame) -> dict[str, Any]:
    q = re.sub(r"\s+", " ", message.lower()).strip()
    delivered = df[df["order_status"].eq("delivered")].copy()
    # The CSV is order-item grain. Collapse to one row per order for order-level delivery KPIs.
    order_delivery = delivered.groupby("order_id", as_index=False).agg(
        delivery_days=("delivery_days", "mean"),
        late_flag=("late_flag", "max"),
    )
    if any(k in q for k in ["help", "what can you", "examples", "what do you know"]):
        return {"answer": "Try asking: “What is total revenue?”, “How many orders?”, “Top product categories by revenue?”, “What is average delivery time?”, “What is the late delivery rate?”, or “Show monthly revenue.”",
                "basis": "Supported questions are calculated from Data/processed/fact_sales.csv."}
    if "late" in q and ("delivery" in q or "order" in q or "rate" in q):
        n = int(order_delivery["order_id"].nunique())
        late = int(order_delivery["late_flag"].sum())
        rate = late / n * 100 if n else 0
        return {"answer": f"{late:,} of {n:,} delivered orders were marked late ({rate:.2f}%).",
                "basis": "Order-level calculation: each delivered order counts once; an order is late if any of its item rows is marked late.",
                "data": {"late_orders": late, "delivered_orders": n, "late_rate_percent": round(rate, 2)}}
    if "delivery" in q and any(k in q for k in ["average", "avg", "time", "days"]):
        avg = order_delivery["delivery_days"].mean()
        return {"answer": f"Average delivery time was {avg:.2f} days across {len(order_delivery):,} delivered orders." if pd.notna(avg) else "Delivery-time data is unavailable.",
                "basis": "Order-level calculation: average item delivery-day values within each delivered order, then average across orders.",
                "data": {"average_delivery_days": round(float(avg), 2) if pd.notna(avg) else None,
                         "delivered_orders": int(len(order_delivery))}}
    if "repeat" in q or "returning customer" in q or "repeat customer" in q:
        cust = df.groupby("customer_unique_id")["order_id"].nunique()
        repeat = int((cust > 1).sum())
        total = int(cust.size)
        rate = repeat / total * 100 if total else 0
        return {"answer": f"{repeat:,} of {total:,} unique customers placed more than one order ({rate:.2f}%).",
                "basis": "Counts distinct order IDs per customer_unique_id in the included fact data.",
                "data": {"repeat_customers": repeat, "unique_customers": total, "repeat_rate_percent": round(rate, 2)}}
    if any(k in q for k in ["top categor", "category", "categories"]):
        result = (df.groupby("category", dropna=False)["sales"].sum()
                  .sort_values(ascending=False).head(5))
        lines = [f"{str(k)}: {money(float(v))}" for k, v in result.items()]
        return {"answer": "Top 5 categories by sales:\n" + "\n".join(lines),
                "basis": "Sum of sales by category from order-item rows; top five sorted descending.",
                "data": [{"category": str(k), "sales": round(float(v), 2)} for k, v in result.items()]}
    if "month" in q or "monthly" in q or "trend" in q:
        monthly = df.assign(month=df["order_purchase_timestamp"].dt.to_period("M").astype(str))
        result = monthly.groupby("month")["sales"].sum().sort_index().tail(12)
        lines = [f"{k}: {money(float(v))}" for k, v in result.items()]
        return {"answer": "Monthly sales for the latest 12 months in the dataset:\n" + "\n".join(lines),
                "basis": "Sum of sales by purchase month; shows the latest 12 months present in the CSV.",
                "data": [{"month": k, "sales": round(float(v), 2)} for k, v in result.items()]}
    if "order" in q or "how many" in q or "count" in q:
        n = int(df["order_id"].nunique())
        return {"answer": f"The included data contains {n:,} distinct orders.",
                "basis": "Distinct order_id count across all statuses in fact_sales.csv.",
                "data": {"orders": n}}
    if "revenue" in q or "sales" in q or "gmv" in q:
        total = float(df["sales"].sum())
        return {"answer": f"Total sales in the included fact data are {money(total)}.",
                "basis": "Sum of the sales column across order-item rows in fact_sales.csv. This is sales, not profit.",
                "data": {"total_sales": round(total, 2)}}
    return {"answer": "I don't have a verified answer for that yet. Ask about total sales/revenue, order count, top categories, monthly sales, average delivery time, late delivery rate, or repeat customers.",
            "basis": "This prototype answers a limited set of predefined questions using the included project data. It does not generate SQL or use an LLM yet."}


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "data_file_found": FACT_PATH.exists()}


@app.post("/api/chat")
def chat(request: ChatRequest):
    try:
        return reply(request.message, load_fact())
    except Exception as exc:
        return {"answer": "I couldn't load the project data. Check the setup instructions and confirm the processed CSV files are present.",
                "basis": str(exc)}
