import { useState } from "react";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Async, Card, DataTable, Note, PageHeader, Pager } from "../components/ui";
import { BarC } from "../components/charts";
import { money, num, pct, pretty } from "../utils/format";

export default function ProductsPage() {
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("revenue");
  const p = useApi(() => api.products({ page, sort }), [page, sort]);
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title="Product Analytics" desc="Category performance, top products and category pairs bought together." />
      <Async state={p}>{(d: any) => (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Category performance" className="lg:col-span-2" right={<select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }} className="rounded-md border border-slate-300 px-2 py-1 text-xs">{["revenue", "orders", "items", "aov", "customers"].map((s) => <option key={s} value={s}>Sort: {s}</option>)}</select>}>
            <DataTable columns={[{ key: "category", label: "Category", render: (v) => pretty(v) }, { key: "revenue", label: "Revenue", align: "right", render: (v) => money(v) }, { key: "orders", label: "Orders", align: "right", render: (v) => num(v) },
              { key: "items", label: "Items", align: "right", render: (v) => num(v) }, { key: "aov", label: "AOV", align: "right", render: (v) => money(v, 2) }, { key: "share_pct", label: "Share", align: "right", render: (v) => pct(v) }, { key: "cumulative_share_pct", label: "Cumulative", align: "right", render: (v) => pct(v) }]} rows={d.categories.items} />
            <Pager page={page} onPage={setPage} hasNext={page * d.categories.page_size < d.categories.category_count} />
          </Card>
          <Card title="Top 15 products by revenue" subtitle="Product IDs are anonymised in Olist (no product names)"><BarC horizontal height={380} data={d.top_products.map((t: any) => ({ ...t, id: `${t.product_id.slice(0, 6)}… ${pretty(t.category)}` }))} x="id" y="revenue" fmt={(v) => money(v)} /></Card>
          <Card title="Categories bought together (market basket)" subtitle="Orders containing both categories"><DataTable columns={[{ key: "category_a", label: "Category A", render: (v) => pretty(v) }, { key: "category_b", label: "Category B", render: (v) => pretty(v) }, { key: "orders_together", label: "Orders", align: "right", render: (v) => num(v) }, { key: "support", label: "Support", align: "right", render: (v) => `${(v * 100).toFixed(3)}%` }]} rows={d.market_basket} /></Card>
        </div>)}</Async>
      <div className="mt-6"><Note>Product review analysis is unavailable: no review data is included in the processed dataset.</Note></div>
    </div>
  );
}
