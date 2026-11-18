from __future__ import annotations

import hmac
import logging
from functools import lru_cache

from fastapi import Header, HTTPException

from ..ai.analyst import Analyst
from ..ai.llm import OpenAILLM
from ..analytics.service import Analytics
from ..core.config import settings
from ..database.session import make_executor

log = logging.getLogger("ecom360")


@lru_cache(maxsize=1)
def get_executor():
    return make_executor(settings)


def get_analytics() -> Analytics:
    return Analytics(get_executor())


@lru_cache(maxsize=1)
def get_analyst() -> Analyst:
    llm = None
    if settings.llm_configured:
        try:
            llm = OpenAILLM(settings.openai_api_key, settings.openai_model)
        except Exception as exc:  # e.g. SDK missing
            log.error("OpenAI client init failed: %s", type(exc).__name__)
    return Analyst(get_executor(), settings, llm=llm)


def require_key(x_api_key: str | None = Header(default=None)) -> None:
    """Optional demo auth: enabled only when APP_API_KEY is set. Not production-grade auth."""
    if settings.app_api_key and not (x_api_key and hmac.compare_digest(x_api_key, settings.app_api_key)):
        raise HTTPException(status_code=401, detail="Missing or invalid API key.")
