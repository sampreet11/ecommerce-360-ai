import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export const PALETTE = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316", "#64748b", "#ec4899"];
const axis = { fontSize: 11, fill: "#64748b" };
const compact = (v: any) => (typeof v === "number" ? (Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : Math.abs(v) >= 1e3 ? `${(v / 1e3).toFixed(0)}K` : String(Math.round(v * 100) / 100)) : String(v));

type Props = { data: any[]; x: string; y: string | string[]; height?: number; fmt?: (v: any) => string; horizontal?: boolean; names?: Record<string, string> };

export function BarC({ data, x, y, height = 280, fmt, horizontal, names }: Props) {
  const ys = Array.isArray(y) ? y : [y];
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ left: horizontal ? 40 : 0, right: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        {horizontal ? <><XAxis type="number" tick={axis} tickFormatter={compact} /><YAxis type="category" dataKey={x} tick={axis} width={110} /></>
          : <><XAxis dataKey={x} tick={axis} interval={0} angle={data.length > 6 ? -30 : 0} textAnchor={data.length > 6 ? "end" : "middle"} height={data.length > 6 ? 70 : 30} /><YAxis tick={axis} tickFormatter={compact} /></>}
        <Tooltip formatter={(v: any, n: any) => [fmt ? fmt(v) : compact(v), names?.[n] ?? n]} />
        {ys.length > 1 && <Legend />}
        {ys.map((k, i) => <Bar key={k} dataKey={k} name={names?.[k] ?? k} fill={PALETTE[i]} radius={[3, 3, 0, 0]} />)}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function LineC({ data, x, y, height = 280, fmt, names }: Props) {
  const ys = Array.isArray(y) ? y : [y];
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ right: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey={x} tick={axis} minTickGap={24} /><YAxis tick={axis} tickFormatter={compact} />
        <Tooltip formatter={(v: any, n: any) => [fmt ? fmt(v) : compact(v), names?.[n] ?? n]} />
        {ys.length > 1 && <Legend />}
        {ys.map((k, i) => <Line key={k} type="monotone" dataKey={k} name={names?.[k] ?? k} stroke={PALETTE[i]} strokeWidth={2} dot={false} strokeDasharray={k.includes("forecast") ? "5 4" : undefined} connectNulls />)}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function PieC({ data, x, y, height = 280, fmt }: Props) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={data} dataKey={y as string} nameKey={x} innerRadius={55} outerRadius={95} paddingAngle={2}>
          {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
        </Pie>
        <Tooltip formatter={(v: any) => (fmt ? fmt(v) : compact(v))} /><Legend wrapperStyle={{ fontSize: 11 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
