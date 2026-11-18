import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Async, Card, DataTable, Kpi, Note, PageHeader } from "../components/ui";
import { BarC, LineC, PieC } from "../components/charts";
import { money, num, pct } from "../utils/format";

function Heat({ matrix }: { matrix: any[] }) {
  const cols = Array.from({ length: 13 }, (_, i) => i);
  const shade = (v?: number) => (v == null ? "transparent" : `rgba(79,70,229,${Math.min(1, 0.12 + v / 12)})`);
  return (
    <div className="overflow-x-auto"><table className="text-[11px]"><thead><tr><th className="px-2 text-left">Cohort</th><th className="px-2">Size</th>{cols.map((c) => <th key={c} className="px-1.5">M{c}</th>)}</tr></thead>
      <tbody>{matrix.map((m) => <tr key={m.cohort_month}><td className="whitespace-nowrap px-2">{m.cohort_month.slice(0, 7)}</td><td className="px-2 text-right">{num(m.cohort_size)}</td>
        {cols.map((c) => <td key={c} className="px-1.5 py-0.5 text-center tabular-nums" style={{ background: shade(m.retention[c]), color: (m.retention[c] ?? 0) > 6 ? "white" : "#1e293b" }}>{m.retention[c] != null ? m.retention[c].toFixed(c === 0 ? 0 : 1) : ""}</td>)}</tr>)}</tbody></table></div>
  );
}

export default function CustomersPage() {
  const c = useApi(() => api.customers(), []);
  const r = useApi(() => api.retention(), []);
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title="Customer Analytics" desc="Repeat purchasing, RFM segmentation and cohort retention. Lifecycle buckets describe time since last purchase, not subscription churn." />
      <Async state={c}>{(d: any) => (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <Kpi label="Customers" value={num(d.metrics.customers)} /><Kpi label="Repeat customers" value={num(d.metrics.repeat_customers)} hint={pct(d.metrics.repeat_customer_pct)} />
            <Kpi label="Repeat revenue share" value={pct(d.metrics.repeat_revenue_share_pct)} /><Kpi label="Snapshot" value="Sep 2018" hint="Recency vs last data date" />
          </div>
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card title="Revenue by RFM segment"><BarC horizontal data={d.rfm_segments} x="rfm_segment" y="revenue" height={300} fmt={(v) => money(v)} /></Card>
            <Card title="New vs repeat customers"><PieC data={d.new_vs_repeat} x="customer_type" y="customers" fmt={(v) => num(v)} /></Card>
            <Card title="Lifecycle (time since last purchase)"><BarC data={d.lifecycle} x="lifecycle" y="customers" fmt={(v) => num(v)} /></Card>
            <Card title="Purchase behaviour"><BarC data={d.metrics.orders_per_customer} x="orders_per_customer" y="customers" fmt={(v) => num(v)} /></Card>
            <Card className="lg:col-span-2" title="RFM segment detail"><DataTable columns={[{ key: "rfm_segment", label: "Segment" }, { key: "customers", label: "Customers", align: "right", render: (v) => num(v) }, { key: "revenue", label: "Revenue", align: "right", render: (v) => money(v) },
              { key: "revenue_share_pct", label: "Share", align: "right", render: (v) => pct(v) }, { key: "avg_orders", label: "Avg orders", align: "right", render: (v) => v?.toFixed(2) }, { key: "avg_recency_days", label: "Avg recency (d)", align: "right", render: (v) => v?.toFixed(0) }]} rows={d.rfm_segments} /></Card>
          </div></>)}</Async>
      <Async state={r}>{(d: any) => (
        <div className="mt-6 grid gap-6">
          <Card title="Average retention curve" subtitle="% of a cohort placing another delivered order k months after first purchase"><LineC data={d.curve.filter((x: any) => x.months_since_first_purchase > 0).map((x: any) => ({ month: `M${x.months_since_first_purchase}`, retention: x.retention_pct }))} x="month" y="retention" fmt={(v) => pct(v, 2)} /></Card>
          <Card title="Cohort retention matrix (%)"><Heat matrix={d.matrix} /></Card>
          <Note>{d.note}</Note>
        </div>)}</Async>
    </div>
  );
}
