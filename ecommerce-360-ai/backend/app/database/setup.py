"""One-shot database setup:  python -m app.database.setup [--force]

1. alembic upgrade head  (tables + views)      2. import processed CSVs (skipped if already loaded)
3. create/refresh the restricted `ai_readonly` role.   Idempotent.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

from ..ai.catalog import ALLOWED
from ..core.config import PROJECT_ROOT, settings
from .loader import load_all

BACKEND = Path(__file__).resolve().parents[2]


def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")


def role_sql(password: str) -> list[str]:
    pw = password.replace("'", "''")
    stmts = [
        "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ai_readonly') THEN CREATE ROLE ai_readonly LOGIN; END IF; END $$",
        f"ALTER ROLE ai_readonly WITH LOGIN PASSWORD '{pw}'",
        "ALTER ROLE ai_readonly SET search_path = analytics",
        "ALTER ROLE ai_readonly SET default_transaction_read_only = on",
        "ALTER ROLE ai_readonly SET statement_timeout = '10s'",
        "REVOKE ALL ON SCHEMA app FROM ai_readonly",
        "REVOKE ALL ON ALL TABLES IN SCHEMA analytics FROM ai_readonly",
        "GRANT USAGE ON SCHEMA analytics TO ai_readonly",
    ]
    stmts += [f"GRANT SELECT ON analytics.{t} TO ai_readonly" for t in ALLOWED]   # allow-list only
    return stmts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="reload data even if tables are populated")
    ap.add_argument("--skip-roles", action="store_true")
    args = ap.parse_args()
    from .session import make_executor  # lazy: keeps role_sql importable without SQLAlchemy
    ex = make_executor(settings)
    for attempt in range(30):  # wait for the DB container
        if ex.ping():
            break
        print(f"waiting for database... ({attempt + 1}/30)"); time.sleep(2)
    else:
        print("ERROR: database not reachable. Check DATABASE_URL / that PostgreSQL is running."); return 1
    print("Running migrations..."); run_migrations()
    n = ex.query("SELECT COUNT(*) AS n FROM analytics.fact_sales")[0]["n"]
    if n and not args.force:
        print(f"fact_sales already has {n:,} rows - skipping import (use --force to reload).")
    else:
        print(f"Importing from {settings.data_dir} ..."); load_all(ex, settings.data_dir)
    if not args.skip_roles:
        pw = os.environ.get("AI_DB_PASSWORD", "")
        if not pw:
            print("AI_DB_PASSWORD not set: skipping creation of the restricted ai_readonly role "
                  "(AI queries will fall back to the main connection inside a READ ONLY transaction).")
        elif not re.fullmatch(r"[A-Za-z0-9_.!@#^*-]{8,64}", pw):
            print("AI_DB_PASSWORD has unsupported characters or length (8-64 of A-Za-z0-9_.!@#^*-)."); return 1
        else:
            for st in role_sql(pw):
                ex.execute(st)
            print("Restricted role ai_readonly configured (SELECT on approved views/tables only).")
    print("Setup complete."); return 0


if __name__ == "__main__":
    sys.exit(main())
