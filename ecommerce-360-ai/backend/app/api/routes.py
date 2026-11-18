from __future__ import annotations

import logging
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ..ai.chat_store import ChatStore
from ..analytics.service import Analytics
from ..core.config import settings
from ..reports import generator
from .deps import get_analyst, get_analytics, get_executor, require_key

log = logging.getLogger("ecom360.api")
public = APIRouter(prefix="/api")
router = APIRouter(prefix="/api", dependencies=[Depends(require_key)])

Start = Query(None, description="Inclusive start purchase month (YYYY-MM-DD)")
End = Query(None, description="Inclusive end purchase month (YYYY-MM-DD)")


def _check(start: date | None, end: date | None):
    if start and end and start > end:
        raise HTTPException(422, "start must be on or before end")


# ---- health / system ----------------------------------------------------------------------
@public.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@router.get("/system/status", tags=["system"])
def system_status(a: Analytics = Depends(get_analytics)):
    db_ok = get_executor().ping()
    out = {"database": "up" if db_ok else "down", "settings": settings.public_dict(),
           "limitations": ["Historical data, not live.", "Revenue is not profit (no cost data).",
                           "Review scores/payments are not loaded.", "Repeat purchasing is not subscription churn."]}
    if db_ok:
        try:
            out["tables"] = a.table_counts(); out["coverage"] = a.coverage()
        except Exception:
            out["database"] = "schema_missing"
            out["hint"] = "Run: python -m app.database.setup (migrations + data import)"
    out["ai_mode"] = "llm" if settings.llm_configured else "offline"
    return out


# ---- dashboard ----------------------------------------------------------------------------
@router.get("/dashboard/overview", tags=["dashboard"])
def d_overview(start: date | None = Start, end: date | None = End, a: Analytics = Depends(get_analytics)):
    _check(start, end); return {**a.overview(start, end), "currency": settings.currency_symbol, "coverage": a.coverage()}


@router.get("/dashboard/revenue-trend", tags=["dashboard"])
def d_trend(start: date | None = Start, end: date | None = End, a: Analytics = Depends(get_analytics)):
    _check(start, end); return {"items": a.revenue_trend(start, end)}


@router.get("/dashboard/top-categories", tags=["dashboard"])
def d_cats(start: date | None = Start, end: date | None = End, limit: int = Query(10, ge=1, le=100),
           sort: Literal["revenue", "orders", "items", "aov", "customers", "freight"] = "revenue",
           page: int = Query(1, ge=1), a: Analytics = Depends(get_analytics)):
    _check(start, end); return a.top_categories(start, end, limit=limit, sort=sort, page=page)


@router.get("/dashboard/delivery-performance", tags=["dashboard"])
def d_delivery(start: date | None = Start, end: date | None = End, a: Analytics = Depends(get_analytics)):
    _check(start, end); return a.delivery_performance(start, end)


@router.get("/dashboard/customer-metrics", tags=["dashboard"])
def d_customers(start: date | None = Start, end: date | None = End, a: Analytics = Depends(get_analytics)):
    _check(start, end); return a.customer_metrics(start, end)


@router.get("/dashboard/review-analysis", tags=["dashboard"])
def d_reviews(a: Analytics = Depends(get_analytics)):
    return a.review_analysis()


# ---- analytics pages ----------------------------------------------------------------------
@router.get("/analytics/sales", tags=["analytics"])
def a_sales(start: date | None = Start, end: date | None = End, a: Analytics = Depends(get_analytics)):
    _check(start, end); return a.sales(start, end)


@router.get("/analytics/customers", tags=["analytics"])
def a_customers(a: Analytics = Depends(get_analytics)):
    return a.customers()


@router.get("/analytics/products", tags=["analytics"])
def a_products(start: date | None = Start, end: date | None = End,
               sort: Literal["revenue", "orders", "items", "aov", "customers", "freight"] = "revenue",
               page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100), a: Analytics = Depends(get_analytics)):
    _check(start, end); return a.products(sort, page, page_size, start, end)


@router.get("/analytics/operations", tags=["analytics"])
def a_ops(start: date | None = Start, end: date | None = End, min_seller_orders: int = Query(30, ge=1),
          page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100), a: Analytics = Depends(get_analytics)):
    _check(start, end); return a.operations(start, end, min_seller_orders, page, page_size)


@router.get("/analytics/retention", tags=["analytics"])
def a_retention(max_months: int = Query(12, ge=1, le=24), a: Analytics = Depends(get_analytics)):
    return a.retention(max_months)


@router.get("/analytics/forecast", tags=["analytics"])
def a_forecast(horizon: int = Query(6, ge=1, le=12), a: Analytics = Depends(get_analytics)):
    return a.forecast(horizon)


# ---- chat ---------------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


@router.post("/chat", tags=["chat"])
def chat(req: ChatRequest):
    return get_analyst().answer(req.message.strip(), req.session_id)


@router.get("/chat/history", tags=["chat"])
def chat_history(session_id: str = Query(..., max_length=64, pattern=r"^[A-Za-z0-9_-]+$")):
    return {"session_id": session_id, "messages": ChatStore(get_executor()).history(session_id, 200)}


@router.delete("/chat/history", tags=["chat"])
def chat_clear(session_id: str = Query(..., max_length=64, pattern=r"^[A-Za-z0-9_-]+$")):
    return {"session_id": session_id, "deleted": ChatStore(get_executor()).clear(session_id)}


# ---- reports ------------------------------------------------------------------------------
@router.get("/reports/summary", tags=["reports"])
def report_summary(start: date | None = Start, end: date | None = End, a: Analytics = Depends(get_analytics)):
    _check(start, end); return generator.build_summary(a, start, end, settings.currency_symbol)


class ReportRequest(BaseModel):
    format: Literal["pdf", "csv", "md"] = "pdf"
    start: date | None = None
    end: date | None = None
    include_ai_narrative: bool = False


@router.post("/reports/generate", tags=["reports"])
def report_generate(req: ReportRequest, a: Analytics = Depends(get_analytics)):
    _check(req.start, req.end)
    s = generator.build_summary(a, req.start, req.end, settings.currency_symbol)
    narrative = None
    analyst = get_analyst()
    if req.include_ai_narrative and analyst.llm:
        try:
            flat = [{"metric": k, "value": v} for k, v in s["kpis"].items()]
            narrative = analyst.llm.narrate("Write a concise executive summary of these KPIs.", "", flat,
                                            "KPIs from the analytics views (delivered orders)")
        except Exception as exc:
            log.error("report narrative failed: %s", type(exc).__name__)
    if req.format == "csv":
        body, mime, ext = generator.to_csv(s), "text/csv", "csv"
    elif req.format == "md":
        body, mime, ext = generator.to_markdown(s, narrative), "text/markdown", "md"
    else:
        body, mime, ext = generator.to_pdf(s, narrative), "application/pdf", "pdf"
    return Response(body, media_type=mime, headers={"Content-Disposition": f'attachment; filename="ecommerce360_summary.{ext}"'})
