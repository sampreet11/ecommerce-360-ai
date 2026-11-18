"""Analyst orchestration with a scripted fake LLM (NO live OpenAI call is made here)."""
import unittest, uuid
from app.ai.analyst import Analyst, ungrounded_numbers, build_chart
from app.ai.chat_store import ChatStore
from app.core.config import load_settings
from .helpers import full_db


class FakeLLM:
    def __init__(self, plans, narration="Top category revenue is R$1,233,131.72."):
        self.plans, self.narration, self.calls = list(plans), narration, []
    def plan(self, q, h): self.calls.append(("plan", q, len(h))); return self.plans.pop(0)
    def repair(self, q, h, sql, err): self.calls.append(("repair", err)); return self.plans.pop(0)
    def narrate(self, q, sql, rows, calc): self.calls.append(("narrate",)); return self.narration


def S(): return load_settings()
def sid(): return "t-" + uuid.uuid4().hex


class Offline(unittest.TestCase):
    def setUp(self): self.a = Analyst(full_db(), S(), llm=None)

    def test_no_key_message_and_real_numbers(self):
        r = self.a.answer("What is our total revenue?", sid())
        self.assertEqual(r["status"], "ok"); self.assertEqual(r["mode"], "offline")
        self.assertIn("OPENAI_API_KEY", r["llm_unavailable_reason"])
        self.assertAlmostEqual(r["rows"][0]["revenue"], 13221498.11, places=1)
        self.assertIn("13,221,498.11", r["answer"]); self.assertIn("v_monthly_kpis", r["sql"])

    def test_top_categories_chart(self):
        r = self.a.answer("Compare revenue across the top five categories.", sid())
        self.assertEqual(len(r["rows"]), 5); self.assertEqual(r["chart"]["type"], "bar")
        self.assertEqual(r["rows"][0]["category"], "health_beauty")
        self.assertEqual(len(r["chart"]["data"]), 5)

    def test_conversational_memory_it(self):
        s = sid()
        self.a.answer("Which category generated the highest revenue?", s)
        r = self.a.answer("How much did it generate?", s)
        self.assertEqual(r["status"], "ok"); self.assertIn("health_beauty", r["answer"])
        self.assertAlmostEqual(r["rows"][0]["revenue"], 1233131.72 - 0, delta=100000)  # delivered-only value
        self.assertEqual(len(self.a.store.history(s)), 4)

    def test_unsupported_reviews_and_profit(self):
        for q in ["Which categories have the lowest ratings?", "What is our profit margin?"]:
            r = self.a.answer(q, sid()); self.assertEqual(r["status"], "unsupported"); self.assertIsNone(r["sql"])

    def test_late_rate_matches_overview(self):
        r = self.a.answer("What percentage of orders were delivered late?", sid())
        self.assertAlmostEqual(r["rows"][0]["late_pct"], 8.1124, places=2)

    def test_insights_non_sql(self):
        r = self.a.answer("Give me three important business recommendations.", sid())
        self.assertEqual(r["status"], "ok"); self.assertIn("Recommendations", r["answer"])

    def test_history_clear(self):
        s = sid(); self.a.answer("total revenue", s)
        self.assertEqual(self.a.store.clear(s), 2); self.assertEqual(self.a.store.history(s), [])


class WithFakeLLM(unittest.TestCase):
    def mk(self, plans, **kw):
        llm = FakeLLM(plans, **kw); return Analyst(full_db(), S(), llm=llm), llm

    def good(self): return {"intent": "sql", "sql": "SELECT category, revenue FROM v_category_kpis ORDER BY revenue DESC LIMIT 5",
                            "calculation": "sum", "chart": {"type": "bar", "x": "category", "y": "revenue"}, "followups": ["next?"]}

    def test_happy_path(self):
        a, llm = self.mk([self.good()], narration="health_beauty leads with R$1,233,131.72.")
        r = a.answer("top categories", sid())
        self.assertEqual(r["status"], "ok"); self.assertEqual(r["mode"], "llm"); self.assertIsNone(r["llm_unavailable_reason"])
        self.assertEqual(r["followups"], ["next?"]); self.assertEqual(len(r["chart"]["data"]), 5)
        self.assertEqual(r["warnings"], [])

    def test_malicious_sql_is_blocked_and_not_executed(self):
        evil = {"intent": "sql", "sql": "DROP TABLE analytics.fact_sales"}
        a, llm = self.mk([evil, evil])
        r = a.answer("drop everything", sid())
        self.assertEqual(r["status"], "rejected"); self.assertIn(("repair", llm.calls[1][1]), llm.calls)
        self.assertGreater(a.ex.query("SELECT COUNT(*) n FROM analytics.fact_sales")[0]["n"], 100000)

    def test_repair_then_success(self):
        a, llm = self.mk([{"intent": "sql", "sql": "SELECT * FROM secrets"}, self.good()])
        r = a.answer("top categories", sid()); self.assertEqual(r["status"], "ok")

    def test_ungrounded_number_flagged(self):
        a, _ = self.mk([self.good()], narration="Revenue was R$99,999,999.00 in total.")
        r = a.answer("top categories", sid())
        self.assertTrue(any("could not be matched" in w for w in r["warnings"]))

    def test_no_rows(self):
        a, _ = self.mk([{"intent": "sql", "sql": "SELECT category FROM v_category_kpis WHERE category = 'nonexistent'"}])
        r = a.answer("x", sid()); self.assertEqual(r["status"], "no_data"); self.assertIn("no rows", r["answer"])

    def test_api_failure_is_graceful(self):
        class Boom(FakeLLM):
            def plan(self, q, h): raise RuntimeError("sk-secret-should-not-leak")
        a = Analyst(full_db(), S(), llm=Boom([])); r = a.answer("x", sid())
        self.assertEqual(r["status"], "error"); self.assertNotIn("sk-secret", str(r))

    def test_row_limit_applied(self):
        s = S(); s.ai_row_limit = 7
        a = Analyst(full_db(), s, llm=FakeLLM([{"intent": "sql", "sql": "SELECT order_id FROM fact_sales"}], narration="ok"))
        r = a.answer("list orders", sid()); self.assertEqual(r["row_count"], 7)
        self.assertTrue(any("truncated" in w for w in r["warnings"]))

    def test_unsupported_from_llm(self):
        a, _ = self.mk([{"intent": "unsupported", "message": "No review data."}])
        r = a.answer("avg review?", sid()); self.assertEqual(r["status"], "unsupported"); self.assertIsNone(r["sql"])


class Helpers(unittest.TestCase):
    def test_grounding(self):
        rows = [{"revenue": 1233131.72, "share": 0.0932}]
        self.assertEqual(ungrounded_numbers("Revenue was R$1,233,131.72 (9.3%) or about 1.2M.", rows), [])
        self.assertTrue(ungrounded_numbers("Revenue was 5,000,000.", rows))
    def test_chart_rejects_bad_columns(self):
        self.assertIsNone(build_chart([{"a": 1}], {"type": "bar", "x": "a", "y": "zzz"}))
        self.assertIsNone(build_chart([{"a": "x", "b": "y"}], {"type": "bar", "x": "a", "y": "b"}))

if __name__ == "__main__":
    unittest.main()
