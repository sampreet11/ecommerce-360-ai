"""Reconciles SQL/view results with independent pandas calculations on the raw processed CSVs."""
import unittest
import pandas as pd
from app.analytics.service import Analytics
from app.analytics.insights import build_insights
from .helpers import DATA, full_db


class Reconcile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = Analytics(full_db())
        f = pd.read_csv(DATA / "fact_sales.csv")
        cls.f = f
        cls.d = f[f.order_status == "delivered"]
        cls.o = cls.d.groupby("order_id").agg(dd=("delivery_days", "max"), lf=("late_flag", "max"),
                                              cu=("customer_unique_id", "max"), rev=("sales", "sum"))

    def test_row_counts_loaded(self):
        c = self.a.table_counts()
        self.assertEqual(c["fact_sales"], len(self.f))
        self.assertEqual(c["customer_360"], 93358)
        self.assertEqual(c["dim_seller"], 3095)

    def test_overview_matches_pandas(self):
        ov = self.a.overview()
        self.assertAlmostEqual(ov["revenue"], self.d.sales.sum(), places=1)
        self.assertEqual(ov["orders"], self.d.order_id.nunique())
        self.assertEqual(ov["customers"], self.d.customer_unique_id.nunique())
        self.assertEqual(ov["items"], len(self.d))
        w = self.o[self.o.dd.notna()]
        self.assertAlmostEqual(ov["avg_delivery_days"], w.dd.mean(), places=4)
        self.assertAlmostEqual(ov["late_delivery_pct"], w.lf.mean() * 100, places=4)
        self.assertAlmostEqual(ov["aov"], self.d.sales.sum() / self.d.order_id.nunique(), places=4)

    def test_orders_not_inflated_by_items(self):
        ov = self.a.overview()
        self.assertLess(ov["orders"], ov["items"])  # grain guard: order count != item rows

    def test_monthly_matches_existing_monthly_kpis_csv(self):
        ref = pd.read_csv(DATA / "monthly_kpis.csv")
        got = {r["month"]: r for r in self.a.revenue_trend()}
        for _, r in ref.iterrows():
            g = got[r.purchase_month]
            self.assertAlmostEqual(g["revenue"], r.revenue, places=1)
            self.assertEqual(g["orders"], r.orders)
            self.assertEqual(g["customers"], r.customers)

    def test_category_matches_existing_category_kpis_csv(self):
        ref = pd.read_csv(DATA / "category_kpis.csv").sort_values("revenue", ascending=False)
        got = self.a.top_categories(limit=100)
        self.assertEqual(got["items"][0]["category"], ref.iloc[0].category)
        self.assertAlmostEqual(got["items"][0]["revenue"], ref.iloc[0].revenue, places=1)
        self.assertEqual(got["category_count"], len(ref))

    def test_forecast_matches_existing_script_output(self):
        ref = pd.read_csv(DATA / "revenue_forecast.csv")
        fc = self.a.forecast()["forecast"]
        for g, (_, r) in zip(fc, ref.iterrows()):
            self.assertEqual(g["month"], r.month)
            self.assertAlmostEqual(g["forecast_revenue"], r.forecast_revenue, places=2)

    def test_date_filter(self):
        from datetime import date
        ov = self.a.overview(date(2017, 1, 1), date(2017, 12, 1))
        d = self.d[(self.d.purchase_month >= "2017-01-01") & (self.d.purchase_month <= "2017-12-01")]
        self.assertAlmostEqual(ov["revenue"], d.sales.sum(), places=1)

    def test_customer_and_rfm(self):
        c = self.a.customers()
        self.assertEqual(sum(s["customers"] for s in c["rfm_segments"]), 93358)
        self.assertAlmostEqual(c["metrics"]["repeat_customer_pct"], (self.o.groupby("cu").size() > 1).mean() * 100, places=3)

    def test_retention_month0_is_100(self):
        r = self.a.retention()
        self.assertAlmostEqual(r["curve"][0]["retention_pct"], 100.0, places=3)
        self.assertLess(r["curve"][1]["retention_pct"], 5)

    def test_review_analysis_reports_unavailable(self):
        self.assertFalse(self.a.review_analysis()["available"])

    def test_insights_have_basis(self):
        ins = build_insights(self.a)
        self.assertGreaterEqual(len(ins), 4)
        for i in ins:
            self.assertTrue(i["basis"]); self.assertIn(i["type"], ("observation", "recommendation"))

    def test_operations_pagination(self):
        o = self.a.operations(page=1, page_size=5)
        self.assertLessEqual(len(o["sellers"]), 5)
        self.assertGreater(o["sellers_total"], 5)

if __name__ == "__main__":
    unittest.main()
