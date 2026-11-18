"""FastAPI entrypoint.  Run: uvicorn app.main:app --reload   (Swagger UI at /docs)"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import public, router
from .core.config import settings
from .core.ratelimit import RateLimiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("ecom360")

app = FastAPI(title="E-Commerce 360° AI Intelligence Platform API", version="1.0.0",
              description="Dashboards, analytics and a grounded natural-language-to-SQL business analyst over the historical Olist dataset.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST", "DELETE"],
                   allow_headers=["Content-Type", "X-API-Key"])

_general = RateLimiter(settings.rate_limit_per_minute)
_chat = RateLimiter(max(5, settings.rate_limit_per_minute // 4))


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    limiter = _chat if (request.url.path.startswith("/api/chat") and request.method == "POST") else _general
    if request.url.path.startswith("/api") and not limiter.allow(f"{ip}:{limiter is _chat}"):
        return JSONResponse({"detail": "Rate limit exceeded. Please slow down."}, status_code=429)
    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.error("unhandled error on %s: %s", request.url.path, type(exc).__name__)
    return JSONResponse({"detail": "Internal server error."}, status_code=500)  # no internals exposed


app.include_router(public)
app.include_router(router)
