import { useState } from "react";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Async, Card, DataTable, DateFilter, Kpi, Note, PageHeader, Pager } from "../components/ui";
import { BarC, LineC } from "../components/charts";
import { days, monthLabel, num, pct } from "../utils/format";
import type { Range } from "../types";

export default function OperationsPage() {
  const [r, setR] = useState<Range>({});
  const [page, setPage] = useState(1);
  const o = useApi(() => api.operations({ ...r, page }), [r.start, r.end, page]);
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title="Operations Analytics" desc="Order-level delivery performance (each order counted once). Late = delivered after the estimated date." right={<DateFilter value={r} onChange={(x) => { setR(x); setPage(1); }} />} />
      <Async state={o}>{(d: any) => (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            <Kpi label="Delivered orders analysed" value={num(d.delivery.overall.orders)} /><Kpi label="Avg delivery time" value={days(d.delivery.overall.avg_delivery_days)} /><Kpi label="Late delivery rate" value={pct(d.delivery.overall.late_delivery_pct)} hint={`${num(d.delivery.overall.late_orders)} late orders`} />
          </div>
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card title="Late-delivery % by month"><LineC data={d.delivery.monthly.map((m: any) => ({ ...m, month: monthLabel(m.month) }))} x="month" y="late_pct" fmt={(v) => pct(v)} /></Card>
            <Card title="Average delivery days by month"><LineC data={d.delivery.monthly.map((m: any) => ({ ...m, month: monthLabel(m.month) }))} x="month" y="avg_delivery_days" fmt={(v) => days(v)} /></Card>
            <Card title="Late % by customer state" subtitle="States with >= 250 orders"><BarC data={d.delivery.by_state.slice(0, 15)} x="state" y="late_pct" fmt={(v) => pct(v)} /></Card>
            <Card title="Avg delivery days by state"><BarC data={[...d.delivery.by_state].sort((a: any, b: any) => b.avg_delivery_days - a.avg_delivery_days).slice(0, 15)} x="state" y="avg_delivery_days" fmt={(v) => days(v)} /></Card>
            <Card className="lg:col-span-2" title="Seller performance" subtitle={`Sellers with >= ${d.min_seller_orders} delivered orders, highest late rate first (${num(d.sellers_total)} sellers)`}>
              <DataTable columns={[{ key: "seller_id", label: "Seller", render: (v) => `${v.slice(0, 8)}…` }, { key: "seller_state", label: "State" }, { key: "orders", label: "Orders", align: "right", render: (v) => num(v) }, { key: "avg_delivery_days", label: "Avg days", align: "right", render: (v) => v?.toFixed(1) }, { key: "late_pct", label: "Late %", align: "right", render: (v) => pct(v) }]} rows={d.sellers} />
              <Pager page={page} onPage={setPage} hasNext={page * d.page_size < d.sellers_total} />
            </Card>
          </div>
          <div className="mt-6"><Note>{d.review_analysis.reason}</Note></div></>)}</Async>
    </div>
  );
}
