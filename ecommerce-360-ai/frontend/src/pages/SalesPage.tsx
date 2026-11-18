import { useState } from "react";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Async, Card, DataTable, DateFilter, PageHeader } from "../components/ui";
import { BarC, LineC } from "../components/charts";
import { money, monthLabel, num, pct, pretty } from "../utils/format";
import type { Range } from "../types";

export default function SalesPage() {
  const [r, setR] = useState<Range>({});
  const s = useApi(() => api.sales(r), [r.start, r.end]);
  const f = useApi(() => api.forecast(), []);
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title="Sales Analytics" desc="Revenue = sum of item price on delivered orders (excludes freight; not profit)." right={<DateFilter value={r} onChange={setR} />} />
      <Async state={s}>{(d: any) => (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Monthly revenue & orders"><LineC data={d.monthly.map((m: any) => ({ ...m, month: monthLabel(m.month) }))} x="month" y="revenue" fmt={(v) => money(v)} /></Card>
          <Card title="Month-over-month change (%)"><BarC data={d.monthly.filter((m: any) => m.mom_growth_pct != null && Math.abs(m.mom_growth_pct) < 150).map((m: any) => ({ month: monthLabel(m.month), mom: Number(m.mom_growth_pct.toFixed(1)) }))} x="month" y="mom" fmt={(v) => pct(v)} /></Card>
          <Card title="Order value distribution" subtitle="Delivered orders by revenue per order"><BarC data={d.order_value_distribution} x="bucket" y="orders" fmt={(v) => num(v)} /></Card>
          <Card title="Top customer states by revenue"><BarC data={d.top_states} x="state" y="revenue" fmt={(v) => money(v)} /></Card>
          <Card className="lg:col-span-2" title="Category performance">
            <DataTable columns={[{ key: "category", label: "Category", render: (v) => pretty(v) }, { key: "revenue", label: "Revenue", align: "right", render: (v) => money(v) }, { key: "orders", label: "Orders", align: "right", render: (v) => num(v) },
              { key: "aov", label: "AOV", align: "right", render: (v) => money(v, 2) }, { key: "share_pct", label: "Share", align: "right", render: (v) => pct(v) }]} rows={d.categories} />
          </Card>
        </div>)}</Async>
      <Card className="mt-6" title="Revenue forecast (baseline)" subtitle="3-month rolling-mean baseline, not a trained ML model; data ends in 2018 so this is illustrative.">
        <Async state={f}>{(d: any) => <LineC data={[...d.history.slice(-12).map((h: any) => ({ month: monthLabel(h.month), revenue: h.revenue })), ...d.forecast.map((h: any) => ({ month: monthLabel(h.month), forecast_revenue: h.forecast_revenue }))]} x="month" y={["revenue", "forecast_revenue"]} fmt={(v) => money(v)} names={{ revenue: "Actual", forecast_revenue: "Forecast" }} />}</Async>
      </Card>
    </div>
  );
}
