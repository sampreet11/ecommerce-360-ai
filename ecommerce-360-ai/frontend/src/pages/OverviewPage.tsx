import { Link } from "react-router-dom";
import { Bot, ArrowRight } from "lucide-react";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Async, Kpi, Note } from "../components/ui";
import { compactMoney, num, pct, days } from "../utils/format";

export default function OverviewPage() {
  const s = useApi(() => api.overview(), []);
  return (
    <div className="mx-auto max-w-6xl">
      <div className="rounded-2xl bg-gradient-to-br from-slate-900 to-brand-700 p-8 text-white sm:p-12">
        <p className="text-xs font-semibold uppercase tracking-widest text-brand-100">Business intelligence + Generative AI</p>
        <h1 className="mt-3 text-3xl font-bold sm:text-4xl">E-Commerce 360° AI Intelligence Platform</h1>
        <p className="mt-3 max-w-2xl text-sm text-slate-200 sm:text-base">Explore the Olist Brazilian e-commerce dataset through executive dashboards and an AI analyst that turns your questions into safe, read-only SQL and explains the real results.</p>
        <Link to="/chat" className="mt-6 inline-flex items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50"><Bot size={16} />Ask the AI Analyst<ArrowRight size={16} /></Link>
      </div>
      <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500">Key business metrics (delivered orders)</h2>
      <Async state={s}>{(d: any) => (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Kpi label="Revenue" value={compactMoney(d.revenue)} hint="Item price, excl. freight" />
            <Kpi label="Orders" value={num(d.orders)} />
            <Kpi label="Customers" value={num(d.customers)} />
            <Kpi label="Late deliveries" value={pct(d.late_delivery_pct)} hint={`Avg ${days(d.avg_delivery_days)}`} />
          </div>
          <div className="mt-4"><Note>Historical data from {d.coverage.first_month?.slice(0, 7)} to {d.coverage.last_month?.slice(0, 7)} - not live. Revenue is not profit (no cost data in Olist).</Note></div>
        </>
      )}</Async>
    </div>
  );
}
