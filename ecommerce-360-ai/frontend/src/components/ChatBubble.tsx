import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronRight, Database, AlertTriangle, User, Bot } from "lucide-react";
import type { ChatMessage } from "../types";
import { BarC, LineC, PieC } from "./charts";
import { pretty } from "../utils/format";

const STATUS_LABEL: Record<string, string> = { unsupported: "Not answerable from this data", rejected: "Blocked by SQL safety checks", no_data: "No data returned", error: "Error" };

function ResultTable({ rows }: { rows: Record<string, any>[] }) {
  if (!rows?.length) return null;
  const cols = Object.keys(rows[0]);
  const fmt = (v: any) => (typeof v === "number" ? v.toLocaleString("en-US", { maximumFractionDigits: 2 }) : String(v ?? ""));
  return (
    <div className="mt-3 max-h-60 overflow-auto rounded-lg border border-slate-200">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-slate-100"><tr>{cols.map((c) => <th key={c} className="px-2 py-1.5 font-medium">{pretty(c)}</th>)}</tr></thead>
        <tbody>{rows.slice(0, 50).map((r, i) => <tr key={i} className="border-t border-slate-100">{cols.map((c) => <td key={c} className="px-2 py-1 tabular-nums">{fmt(r[c])}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export default function ChatBubble({ m, onFollowup }: { m: ChatMessage; onFollowup: (q: string) => void }) {
  const [showSql, setShowSql] = useState(false);
  const [showData, setShowData] = useState(false);
  if (m.role === "user")
    return (
      <div className="flex justify-end gap-2">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-sm text-white">{m.content}</div>
        <span className="mt-1 hidden h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-200 sm:flex"><User size={14} /></span>
      </div>
    );
  const bad = m.status && STATUS_LABEL[m.status];
  const ch = m.chart;
  return (
    <div className="flex gap-2">
      <span className="mt-1 hidden h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700 sm:flex"><Bot size={14} /></span>
      <div className="min-w-0 max-w-[92%] rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm">
        {bad && <div className="mb-2 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800"><AlertTriangle size={11} />{bad}</div>}
        <div className="prose-chat text-sm leading-relaxed text-slate-800"><ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown></div>
        {ch && ch.data?.length > 0 && (
          <div className="mt-3 rounded-lg border border-slate-100 p-2">
            {ch.type === "line" ? <LineC data={ch.data} x={ch.x} y={ch.y} height={220} /> : ch.type === "pie" ? <PieC data={ch.data} x={ch.x} y={ch.y} height={220} /> : <BarC data={ch.data} x={ch.x} y={ch.y} height={240} />}
          </div>
        )}
        {m.warnings && m.warnings.length > 0 && <ul className="mt-2 space-y-1 text-xs text-amber-700">{m.warnings.map((w, i) => <li key={i}>⚠ {w}</li>)}</ul>}
        {(m.sql || (m.rows && m.rows.length > 0)) && (
          <div className="mt-3 space-y-1 border-t border-slate-100 pt-2 text-xs">
            {m.sql && (
              <button onClick={() => setShowSql(!showSql)} className="flex items-center gap-1 font-medium text-slate-600 hover:text-brand-600">
                {showSql ? <ChevronDown size={14} /> : <ChevronRight size={14} />}<Database size={12} />How was this calculated? (SQL)
              </button>
            )}
            {showSql && (
              <div className="rounded-lg bg-slate-900 p-3 text-slate-100">
                <pre className="overflow-x-auto whitespace-pre-wrap text-[11px]">{m.sql}</pre>
                {m.data_source && <p className="mt-2 text-[11px] text-slate-400">Source: {m.data_source}</p>}
                {m.calculation && <p className="mt-1 text-[11px] text-slate-300">{m.calculation}</p>}
                <p className="mt-1 text-[11px] text-slate-400">Executed read-only; {m.row_count ?? 0} row(s) returned. Mode: {m.mode}.</p>
              </div>
            )}
            {m.rows && m.rows.length > 0 && (
              <button onClick={() => setShowData(!showData)} className="flex items-center gap-1 font-medium text-slate-600 hover:text-brand-600">
                {showData ? <ChevronDown size={14} /> : <ChevronRight size={14} />}Result data ({m.row_count ?? m.rows.length} rows)
              </button>
            )}
            {showData && m.rows && <ResultTable rows={m.rows} />}
          </div>
        )}
        {m.followups && m.followups.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">{m.followups.map((f) => <button key={f} onClick={() => onFollowup(f)} className="rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-xs text-brand-700 hover:bg-brand-100">{f}</button>)}</div>
        )}
      </div>
    </div>
  );
}
