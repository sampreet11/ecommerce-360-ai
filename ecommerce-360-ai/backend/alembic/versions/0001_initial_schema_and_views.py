"""Initial analytics schema, chat tables and analytical views.

The SQL files under database/schema and database/views are the single source of truth.
"""
from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

ROOT = Path(__file__).resolve().parents[3]


def _statements(path: Path) -> list[str]:
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def upgrade() -> None:
    bind = op.get_bind()
    for f in (ROOT / "database" / "schema" / "001_schema.sql", ROOT / "database" / "views" / "001_views.sql"):
        for stmt in _statements(f):
            bind.exec_driver_sql(stmt)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP SCHEMA IF EXISTS app CASCADE")
    bind.exec_driver_sql("DROP SCHEMA IF EXISTS analytics CASCADE")
