import { useState } from "react";
import { Clock, DollarSign, Package, Repeat, ShoppingBag, Star, Truck, Users } from "lucide-react";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Async, Card, DateFilter, Kpi, Note, PageHeader } from "../components/ui";
import { BarC, LineC, PieC } from "../components/charts";
import { compactMoney, days, monthLabel, money, num, pct, pretty } from "../utils/format";
import type { Range } from "../types";

export default function DashboardPage() {
  const [r, setR] = useState<Range>({});
  const ov = useApi(() => api.overview(r), [r.start, r.end]);
  const tr = useApi(() => api.revenueTrend(r), [r.start, r.end]);
  const cats = useApi(() => api.topCategories(r, 10), [r.start, r.end]);
  const dl = useApi(() => api.delivery(r), [r.start, r.end]);
  const cm = useApi(() => api.customerMetrics(r), [r.start, r.end]);
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title="Executive Dashboard" desc="All figures are computed by the backend from PostgreSQL. Delivered orders unless stated." right={<DateFilter value={r} onChange={setR} />} />
      <Async state={ov}>{(d: any) => (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Kpi label="Total revenue" value={compactMoney(d.revenue)} hint={money(d.revenue)} icon={<DollarSign size={15} />} />
          <Kpi label="Total orders" value={num(d.orders)} hint={`${num(d.items)} items`} icon={<ShoppingBag size={15} />} />
          <Kpi label="Customers" value={num(d.customers)} icon={<Users size={15} />} />
          <Kpi label="Avg order value" value={money(d.aov, 2)} icon={<Package size={15} />} />
          <Kpi label="Avg delivery time" value={days(d.avg_delivery_days)} icon={<Clock size={15} />} />
          <Kpi label="Late deliveries" value={pct(d.late_delivery_pct)} hint={`${num(d.late_orders)} orders`} icon={<Truck size={15} />} />
          <Kpi label="Repeat customers" value={pct(d.repeat_customer_pct)} hint="2+ delivered orders" icon={<Repeat size={15} />} />
          <Kpi label="Avg review score" value="n/a" hint="Reviews not in loaded data" icon={<Star size={15} />} />
        </div>)}</Async>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card title="Monthly revenue trend" subtitle="Delivered orders by purchase month"><Async state={tr}>{(d: any) => <LineC data={d.items.map((i: any) => ({ ...i, month: monthLabel(i.month) }))} x="month" y="revenue" fmt={(v) => money(v)} />}</Async></Card>
        <Card title="Revenue by category (top 10)"><Async state={cats}>{(d: any) => <BarC horizontal height={300} data={d.items.map((i: any) => ({ ...i, category: pretty(i.category) }))} x="category" y="revenue" fmt={(v) => money(v)} />}</Async></Card>
        <Card title="Order status distribution" subtitle="All statuses (not only delivered)"><Async state={ov}>{(d: any) => <PieC data={d.status_distribution} x="order_status" y="orders" fmt={(v) => num(v)} />}</Async></Card>
        <Card title="Delivery time distribution" subtitle="Delivered orders with a delivery date"><Async state={dl}>{(d: any) => <BarC data={d.distribution} x="bucket" y="orders" fmt={(v) => num(v)} />}</Async></Card>
        <Card title="Late-delivery rate by state" subtitle={`Customer states with >= ${250} orders`}><Async state={dl}>{(d: any) => <BarC data={d.by_state.slice(0, 12)} x="state" y="late_pct" fmt={(v) => pct(v)} />}</Async></Card>
        <Card title="Customer purchase patterns" subtitle="Customers by number of delivered orders"><Async state={cm}>{(d: any) => <BarC data={d.orders_per_customer} x="orders_per_customer" y="customers" fmt={(v) => num(v)} />}</Async></Card>
      </div>
      <div className="mt-6"><Note>Review score distribution is not shown: the processed dataset in this project has no reviews table. See <code>docs/data-dictionary.md</code> for how to add it.</Note></div>
    </div>
  );
}
