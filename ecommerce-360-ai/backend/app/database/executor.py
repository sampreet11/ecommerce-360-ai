"""Tiny database abstraction so business logic is independent of the driver.

Production: SQLAlchemyExecutor (PostgreSQL). Tests: SQLiteExecutor.
SQL uses :named parameters, which both drivers accept.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any, Protocol


class Executor(Protocol):
    def query(self, sql: str, params: dict | None = None) -> list[dict[str, Any]]: ...
    def execute(self, sql: str, params: dict | None = None) -> None: ...
    def executemany(self, sql: str, rows: list[dict]) -> None: ...
    def query_readonly(self, sql: str, timeout_ms: int) -> list[dict[str, Any]]: ...
    def ping(self) -> bool: ...


class SQLAlchemyExecutor:
    """Executor over SQLAlchemy engines. `engine` is read/write; `ro_engine` is the
    restricted role used for AI-generated SQL (falls back to `engine` with READ ONLY txn)."""

    def __init__(self, engine, ro_engine=None):
        from sqlalchemy import text  # imported lazily so unit tests need no SQLAlchemy
        self._text = text
        self.engine = engine
        self.ro_engine = ro_engine or engine

    def query(self, sql, params=None):
        with self.engine.connect() as conn:
            res = conn.execute(self._text(sql), params or {})
            return [dict(r._mapping) for r in res]

    def execute(self, sql, params=None):
        with self.engine.begin() as conn:
            conn.execute(self._text(sql), params or {})

    def executemany(self, sql, rows):
        if not rows:
            return
        with self.engine.begin() as conn:
            conn.execute(self._text(sql), rows)

    def query_readonly(self, sql, timeout_ms):
        with self.ro_engine.connect() as conn:
            conn.execute(self._text("SET TRANSACTION READ ONLY"))
            conn.execute(self._text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
            res = conn.execute(self._text(sql))
            rows = [dict(r._mapping) for r in res]
            conn.rollback()
            return rows

    def ping(self):
        try:
            self.query("SELECT 1 AS ok")
            return True
        except Exception:
            return False


def _adapt_date(d: date) -> str:
    return d.isoformat()


def _adapt_dt(d: datetime) -> str:
    return d.strftime("%Y-%m-%d %H:%M:%S")


class SQLiteExecutor:
    """Used by the test suite (schemas emulated with ATTACH ... AS analytics / app)."""

    def __init__(self, path: str = ":memory:"):
        sqlite3.register_adapter(date, _adapt_date)
        sqlite3.register_adapter(datetime, _adapt_dt)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("ATTACH DATABASE ':memory:' AS analytics")
        self.conn.execute("ATTACH DATABASE ':memory:' AS app")

    def script(self, sql: str) -> None:
        # Drop PostgreSQL-only statements for the SQLite test double.
        # (indexes are skipped too: SQLite wants schema-qualified index names, PostgreSQL forbids them)
        skip = ("CREATE SCHEMA", "CREATE INDEX")
        lines = [l for l in sql.splitlines() if not l.strip().upper().startswith(skip)]
        self.conn.executescript("\n".join(lines))

    def query(self, sql, params=None):
        return [dict(r) for r in self.conn.execute(sql, params or {}).fetchall()]

    def execute(self, sql, params=None):
        self.conn.execute(sql, params or {})
        self.conn.commit()

    def executemany(self, sql, rows):
        self.conn.executemany(sql, rows)
        self.conn.commit()

    def query_readonly(self, sql, timeout_ms):
        self.conn.execute("PRAGMA query_only = ON")
        try:
            return [dict(r) for r in self.conn.execute(sql).fetchall()]
        finally:
            self.conn.execute("PRAGMA query_only = OFF")

    def ping(self):
        return True
