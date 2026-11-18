export const CUR = "R$";
export const money = (v: number | null | undefined, d = 0) =>
  v == null ? "n/a" : `${CUR}${v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d })}`;
export const compactMoney = (v: number | null | undefined) =>
  v == null ? "n/a" : v >= 1e6 ? `${CUR}${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `${CUR}${(v / 1e3).toFixed(1)}K` : `${CUR}${v.toFixed(0)}`;
export const num = (v: number | null | undefined) => (v == null ? "n/a" : v.toLocaleString("en-US", { maximumFractionDigits: 0 }));
export const pct = (v: number | null | undefined, d = 1) => (v == null ? "n/a" : `${v.toFixed(d)}%`);
export const days = (v: number | null | undefined) => (v == null ? "n/a" : `${v.toFixed(1)} days`);
export const monthLabel = (iso: string) => iso?.slice(0, 7);
export const pretty = (s: string) => s?.replace(/_/g, " ");
export function toMonthStart(v: string): string | undefined { return v ? `${v}-01` : undefined; }
