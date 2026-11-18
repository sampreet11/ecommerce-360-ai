import unittest
from app.ai.sql_guard import validate, enforce_limit

class Guard(unittest.TestCase):
    def ok(self, s): r = validate(s); self.assertTrue(r.ok, r.reason); return r
    def bad(self, s, frag=""):
        r = validate(s); self.assertFalse(r.ok, f"should reject: {s}")
        self.assertIn(frag.lower(), r.reason.lower()); return r

    def test_accepts_valid_selects(self):
        self.ok("SELECT category, SUM(revenue) AS r FROM analytics.v_category_kpis GROUP BY 1 ORDER BY 2 DESC LIMIT 5;")
        self.ok("WITH m AS (SELECT purchase_month, revenue FROM v_monthly_kpis) SELECT * FROM m")
        self.ok("SELECT EXTRACT(YEAR FROM purchase_month) AS y, SUM(revenue) FROM v_monthly_kpis GROUP BY 1")
        self.ok("SELECT f.category FROM fact_sales f JOIN customer_360 c ON c.customer_unique_id = f.customer_unique_id")
        self.ok("SELECT replace(category, '_', ' ') AS c FROM v_category_kpis")

    def test_rejects_modification(self):
        for s in ["DROP TABLE analytics.fact_sales", "DELETE FROM fact_sales", "UPDATE fact_sales SET sales = 0",
                  "INSERT INTO fact_sales VALUES (1)", "TRUNCATE fact_sales", "ALTER TABLE fact_sales ADD x int",
                  "CREATE TABLE t AS SELECT 1", "GRANT ALL ON fact_sales TO public", "COPY fact_sales TO '/tmp/x'"]:
            self.bad(s)

    def test_rejects_smuggled_modification(self):
        self.bad("WITH x AS (DELETE FROM fact_sales RETURNING *) SELECT * FROM x", "DELETE")
        self.bad("SELECT * INTO newt FROM fact_sales", "INTO")

    def test_rejects_multiple_statements(self):
        self.bad("SELECT 1 FROM fact_sales; DROP TABLE fact_sales", "multiple")
        self.bad("SELECT 1 FROM fact_sales;;", "multiple")

    def test_rejects_comments_and_quoting_tricks(self):
        self.bad("SELECT * FROM fact_sales -- hi", "comment")
        self.bad("SELECT * FROM fact_sales /* x */", "comment")
        self.bad("SELECT * FROM fact_sales WHERE category = $$x$$", "dollar")
        self.bad('SELECT * FROM "fact_sales"', "quoted")

    def test_rejects_unapproved_tables_and_schemas(self):
        self.bad("SELECT * FROM users", "not approved")
        self.bad("SELECT * FROM public.fact_sales", "schema")
        self.bad("SELECT * FROM app.chat_messages", "schema")
        self.bad("SELECT * FROM information_schema.tables", "information_schema")
        self.bad("SELECT * FROM pg_catalog.pg_user", "pg_catalog")
        self.bad("SELECT * FROM fact_sales, secrets", "not approved")
        self.bad("SELECT * FROM dim_seller", "not approved")

    def test_rejects_unknown_columns(self):
        self.bad("SELECT f.password FROM fact_sales f", "does not exist")

    def test_rejects_dangerous_functions(self):
        self.bad("SELECT pg_sleep(10) FROM fact_sales", "pg_sleep")
        self.bad("SELECT pg_read_file('/etc/passwd') FROM fact_sales", "pg_read_file")
        self.bad("SELECT set_config('x','y',false) FROM fact_sales", "set_config")

    def test_rejects_empty_and_tableless(self):
        self.bad("", "empty"); self.bad("   ", "empty"); self.bad("SELECT 1", "approved")

    def test_limit_wrapper(self):
        self.assertEqual(enforce_limit("SELECT 1 FROM fact_sales", 500),
                         "SELECT * FROM (SELECT 1 FROM fact_sales) AS guarded_q LIMIT 500")

if __name__ == "__main__":
    unittest.main()
