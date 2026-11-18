"""Creates the SQLAlchemy engines. The AI engine should use the restricted `ai_readonly` role."""
from __future__ import annotations

from sqlalchemy import create_engine

from ..core.config import Settings
from .executor import SQLAlchemyExecutor


def make_executor(s: Settings) -> SQLAlchemyExecutor:
    engine = create_engine(s.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)
    ro = engine
    if s.ai_database_url and s.ai_database_url != s.database_url:
        ro = create_engine(s.ai_database_url, pool_pre_ping=True, pool_size=3, max_overflow=2)
    return SQLAlchemyExecutor(engine, ro)
