import unittest
from app.core.ratelimit import RateLimiter
from app.core.config import load_settings
from app.database.loader import prepare_table, TABLE_COLUMNS
from app.database.setup import role_sql
from app.ai.catalog import ALLOWED
from app.reports import generator
from app.analytics.service import Analytics
from .helpers import DATA, full_db


class Misc(unittest.TestCase):
    def test_rate_limiter(self):
        r = RateLimiter(2)
        self.assertEqual([r.allow("a", 0), r.allow("a", 1), r.allow("a", 2), r.allow("b", 2), r.allow("a", 61.5)],
                         [True, True, False, True, True])

    def test_settings_never_expose_secrets(self):
        s = load_settings(); s.openai_api_key = "sk-real-looking-key"; s.database_url = "postgresql://u:pw@h/db"
        blob = str(s.public_dict())
        self.assertNotIn("sk-real", blob); self.assertNotIn("pw@", blob); self.assertTrue(s.public_dict()["llm_configured"])

    def test_placeholder_key_counts_as_missing(self):
        s = load_settings(); s.openai_api_key = "sk-your-key-here"; self.assertFalse(s.llm_configured)
        s.openai_api_key = ""; self.assertFalse(s.llm_configured)

    def test_loader_types_and_pk_uniqueness(self):
        rows = prepare_table("fact_sales", DATA)
        self.assertEqual(len({(r["order_id"], r["order_item_id"]) for r in rows}), len(rows))
        r0 = rows[0]; self.assertIn(r0["late_flag"], (0, 1)); self.assertEqual(set(r0), set(TABLE_COLUMNS["fact_sales"]))
        self.assertTrue(hasattr(r0["purchase_month"], "year"))
        nulls = sum(r["delivery_days"] is None for r in rows); self.assertEqual(nulls, 2454)  # matches profiled NaN count

    def test_loader_missing_file_message(self):
        import tempfile, pathlib
        with self.assertRaises(FileNotFoundError): prepare_table("fact_sales", pathlib.Path(tempfile.mkdtemp()))

    def test_role_sql_grants_only_allowlist_and_no_writes(self):
        sql = "\n".join(role_sql("S3cretPassw0rd"))
        for t in ALLOWED: self.assertIn(f"GRANT SELECT ON analytics.{t} ", sql + " ")
        self.assertNotIn("dim_seller TO", sql); self.assertNotIn("INSERT", sql); self.assertIn("REVOKE ALL ON SCHEMA app", sql)
        self.assertIn("default_transaction_read_only = on", sql)
        self.assertIn("'It''s", "\n".join(role_sql("It's12345")))   # quote escaping

    def test_reports_generate_all_formats(self):
        s = generator.build_summary(Analytics(full_db()))
        self.assertTrue(generator.to_pdf(s).startswith(b"%PDF"))
        self.assertIn(b"revenue,13221498.11", generator.to_csv(s))
        md = generator.to_markdown(s).decode(); self.assertIn("not profit", md); self.assertIn("basis:", md)

    def test_db_level_readonly_blocks_writes(self):
        import sqlite3
        ex = full_db()
        with self.assertRaises(sqlite3.OperationalError):
            ex.query_readonly("DELETE FROM analytics.fact_sales", 1000)
        self.assertGreater(ex.query("SELECT COUNT(*) n FROM analytics.fact_sales")[0]["n"], 100000)

if __name__ == "__main__":
    unittest.main()
