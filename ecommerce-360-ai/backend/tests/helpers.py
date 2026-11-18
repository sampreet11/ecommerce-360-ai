from __future__ import annotations
from pathlib import Path
from functools import lru_cache
from app.core.config import PROJECT_ROOT
from app.database.executor import SQLiteExecutor
from app.database.loader import load_all

DATA = PROJECT_ROOT / "data" / "processed"

@lru_cache(maxsize=1)
def full_db() -> SQLiteExecutor:
    """SQLite test double loaded with the real processed CSVs and the real DDL/views."""
    ex = SQLiteExecutor()
    ex.script((PROJECT_ROOT / "database" / "schema" / "001_schema.sql").read_text())
    load_all(ex, DATA, log=lambda *_: None)
    ex.script((PROJECT_ROOT / "database" / "views" / "001_views.sql").read_text())
    return ex
