import { useState } from "react";
import { Download } from "lucide-react";
import { api, errorMessage } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Async, Card, DateFilter, ErrorBox, PageHeader } from "../components/ui";
import { money, num, pct, days, pretty } from "../utils/format";
import type { Range } from "../types";

export default function ReportsPage() {
  const [r, setR] = useState<Range>({});
  const [ai, setAi] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const s = useApi(() => api.reportSummary(r), [r.start, r.end]);
  async function dl(f: "pdf" | "csv" | "md") { setBusy(true); setErr(null); try { await api.downloadReport(f, r, ai); } catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); } }
  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title="Reports" desc="Generate a business summary from live database results." right={<DateFilter value={r} onChange={setR} />} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {(["pdf", "csv", "md"] as const).map((f) => <button key={f} disabled={busy} onClick={() => dl(f)} className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"><Download size={14} />{f.toUpperCase()}</button>)}
        <label className="flex items-center gap-2 text-xs text-slate-600"><input type="checkbox" checked={ai} onChange={(e) => setAi(e.target.checked)} />Include AI narrative (needs OpenAI key)</label>
      </div>
      {err && <ErrorBox message={err} />}
      <Async state={s}>{(d: any) => (
        <Card title={d.title} subtitle={`${d.period.start} to ${d.period.end}`}>
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
            {[["Revenue", money(d.kpis.revenue)], ["Orders", num(d.kpis.orders)], ["Customers", num(d.kpis.customers)], ["AOV", money(d.kpis.aov, 2)], ["Avg delivery", days(d.kpis.avg_delivery_days)], ["Late deliveries", pct(d.kpis.late_delivery_pct)]].map(([k, v]) => <div key={k}><dt className="text-xs text-slate-500">{k}</dt><dd className="font-semibold">{v}</dd></div>)}
          </dl>
          <h4 className="mb-2 mt-5 text-sm font-semibold">Top categories</h4>
          <ol className="list-decimal space-y-1 pl-5 text-sm">{d.top_categories.slice(0, 5).map((c: any) => <li key={c.category}>{pretty(c.category)} - {money(c.revenue)} ({pct(c.share_pct)})</li>)}</ol>
          <h4 className="mb-2 mt-5 text-sm font-semibold">Insights</h4>
          <ul className="space-y-2 text-sm">{d.insights.map((i: any, k: number) => <li key={k}><span className={`mr-2 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${i.type === "observation" ? "bg-sky-100 text-sky-700" : "bg-emerald-100 text-emerald-700"}`}>{i.type}</span><b>{i.title}.</b> {i.text} <span className="text-xs text-slate-400">Basis: {i.basis}</span></li>)}</ul>
          <ul className="mt-5 list-disc space-y-1 pl-5 text-xs text-slate-500">{d.definitions.map((x: string) => <li key={x}>{x}</li>)}</ul>
        </Card>)}</Async>
    </div>
  );
}
