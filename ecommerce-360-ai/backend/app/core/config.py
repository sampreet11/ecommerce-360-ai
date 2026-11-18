"""Application settings, read from environment variables (and an optional .env file).

No secrets are hardcoded. `public_dict()` is the only view of settings that may be
returned by an API endpoint and it never contains keys, passwords or connection URLs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _load_dotenv() -> None:
    for candidate in (PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"):
        if candidate.is_file():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass
class Settings:
    database_url: str = ""
    ai_database_url: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    app_api_key: str = ""           # optional demo auth; empty = disabled
    cors_origins: list[str] = field(default_factory=list)
    rate_limit_per_minute: int = 60
    ai_row_limit: int = 500
    ai_statement_timeout_ms: int = 8000
    chat_history_turns: int = 6
    currency_symbol: str = "R$"
    data_dir: Path = PROJECT_ROOT / "data" / "processed"
    snapshot_note: str = "Historical Olist data (2016-09 to 2018-09); not live."

    @property
    def llm_configured(self) -> bool:
        return bool(self.openai_api_key and not self.openai_api_key.startswith("sk-your"))

    def public_dict(self) -> dict:
        return {
            "llm_configured": self.llm_configured,
            "openai_model": self.openai_model,
            "auth_enabled": bool(self.app_api_key),
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "ai_row_limit": self.ai_row_limit,
            "ai_statement_timeout_ms": self.ai_statement_timeout_ms,
            "currency_symbol": self.currency_symbol,
        }


def load_settings() -> Settings:
    _load_dotenv()
    e = os.environ.get
    return Settings(
        database_url=e("DATABASE_URL", "postgresql+psycopg://ecom:ecom_dev_password@localhost:5432/ecommerce360"),
        ai_database_url=e("AI_DATABASE_URL", e("DATABASE_URL", "")),
        openai_api_key=e("OPENAI_API_KEY", ""),
        openai_model=e("OPENAI_MODEL", "gpt-4o-mini"),
        app_api_key=e("APP_API_KEY", ""),
        cors_origins=[o.strip() for o in e("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()],
        rate_limit_per_minute=_int("RATE_LIMIT_PER_MINUTE", 60),
        ai_row_limit=_int("AI_ROW_LIMIT", 500),
        ai_statement_timeout_ms=_int("AI_STATEMENT_TIMEOUT_MS", 8000),
        chat_history_turns=_int("CHAT_HISTORY_TURNS", 6),
        currency_symbol=e("CURRENCY_SYMBOL", "R$"),
        data_dir=Path(e("DATA_DIR", str(PROJECT_ROOT / "data" / "processed"))),
    )


settings = load_settings()
