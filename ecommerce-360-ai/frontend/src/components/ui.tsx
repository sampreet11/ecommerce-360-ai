import { ReactNode, useState } from "react";
import { AlertTriangle, Info } from "lucide-react";
import type { Range } from "../types";

export const Card = ({ title, subtitle, children, right, className = "" }: { title?: string; subtitle?: string; children: ReactNode; right?: ReactNode; className?: string }) => (
  <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
    {(title || right) && (
      <header className="mb-4 flex items-start justify-between gap-3">
        <div><h3 className="text-sm font-semibold text-slate-900">{title}</h3>{subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}</div>{right}
      </header>
    )}
    {children}
  </section>
);

export const Kpi = ({ label, value, hint, icon }: { label: string; value: string; hint?: string; icon?: ReactNode }) => (
  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
    <div className="flex items-center justify-between text-xs font-medium uppercase tracking-wide text-slate-500">{label}{icon}</div>
    <div className="mt-2 text-2xl font-semibold text-slate-900">{value}</div>
    {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
  </div>
);

export const Loading = ({ label = "Loading..." }: { label?: string }) => (
  <div className="flex items-center gap-2 p-6 text-sm text-slate-500"><span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />{label}</div>
);

export const ErrorBox = ({ message }: { message: string }) => (
  <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"><AlertTriangle size={16} className="mt-0.5 shrink-0" />{message}</div>
);

export const Note = ({ children }: { children: ReactNode }) => (
  <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"><Info size={14} className="mt-0.5 shrink-0" />{children}</div>
);

export function PageHeader({ title, desc, right }: { title: string; desc?: string; right?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-xl font-semibold text-slate-900 sm:text-2xl">{title}</h1>{desc && <p className="mt-1 max-w-3xl text-sm text-slate-500">{desc}</p>}</div>{right}
    </div>
  );
}

export function DateFilter({ value, onChange }: { value: Range; onChange: (r: Range) => void }) {
  const m = (iso?: string) => (iso ? iso.slice(0, 7) : "");
  const set = (k: "start" | "end") => (e: React.ChangeEvent<HTMLInputElement>) => onChange({ ...value, [k]: e.target.value ? `${e.target.value}-01` : undefined });
  const cls = "rounded-md border border-slate-300 bg-white px-2 py-1 text-sm";
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
      <label>From <input type="month" className={cls} min="2016-09" max="2018-09" value={m(value.start)} onChange={set("start")} /></label>
      <label>To <input type="month" className={cls} min="2016-09" max="2018-09" value={m(value.end)} onChange={set("end")} /></label>
      {(value.start || value.end) && <button className="rounded-md px-2 py-1 text-brand-600 hover:bg-brand-50" onClick={() => onChange({})}>Reset</button>}
    </div>
  );
}

export function DataTable({ columns, rows, empty = "No data." }: { columns: { key: string; label: string; render?: (v: any, row: any) => ReactNode; align?: "right" }[]; rows: any[]; empty?: string }) {
  if (!rows?.length) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead><tr className="border-b border-slate-200 text-xs uppercase text-slate-500">{columns.map((c) => <th key={c.key} className={`px-2 py-2 font-medium ${c.align === "right" ? "text-right" : ""}`}>{c.label}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => (
          <tr key={i} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
            {columns.map((c) => <td key={c.key} className={`px-2 py-2 ${c.align === "right" ? "text-right tabular-nums" : ""}`}>{c.render ? c.render(r[c.key], r) : String(r[c.key] ?? "")}</td>)}
          </tr>))}</tbody>
      </table>
    </div>
  );
}

export function Pager({ page, onPage, hasNext }: { page: number; onPage: (p: number) => void; hasNext: boolean }) {
  return (
    <div className="mt-3 flex items-center justify-end gap-2 text-xs">
      <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="rounded border px-2 py-1 disabled:opacity-40">Prev</button>
      <span>Page {page}</span>
      <button disabled={!hasNext} onClick={() => onPage(page + 1)} className="rounded border px-2 py-1 disabled:opacity-40">Next</button>
    </div>
  );
}

export function Async<T>({ state, children }: { state: { data: T | null; error: string | null; loading: boolean }; children: (d: T) => ReactNode }) {
  if (state.loading && !state.data) return <Loading />;
  if (state.error) return <ErrorBox message={state.error} />;
  return state.data ? <>{children(state.data)}</> : null;
}

export const useToggle = (initial = false) => { const [v, set] = useState(initial); return [v, () => set((x) => !x)] as const; };
