import axios from "axios";
import type { ChatResponse, Range } from "../types";

// Optional demo auth header. Only set VITE_API_KEY if APP_API_KEY is enabled on the backend.
const key = import.meta.env.VITE_API_KEY as string | undefined;
const http = axios.create({ baseURL: "/api", timeout: 90_000, headers: key ? { "X-API-Key": key } : {} });

const clean = (r?: Range & Record<string, any>) => Object.fromEntries(Object.entries(r ?? {}).filter(([, v]) => v !== undefined && v !== ""));
const get = <T = any>(url: string, params?: Record<string, any>) => http.get<T>(url, { params: clean(params) }).then((r) => r.data);

export const api = {
  status: () => get("/system/status"),
  overview: (r?: Range) => get("/dashboard/overview", r),
  revenueTrend: (r?: Range) => get("/dashboard/revenue-trend", r),
  topCategories: (r?: Range, limit = 10) => get("/dashboard/top-categories", { ...r, limit }),
  delivery: (r?: Range) => get("/dashboard/delivery-performance", r),
  customerMetrics: (r?: Range) => get("/dashboard/customer-metrics", r),
  reviews: () => get("/dashboard/review-analysis"),
  sales: (r?: Range) => get("/analytics/sales", r),
  customers: () => get("/analytics/customers"),
  products: (r?: Range & { sort?: string; page?: number }) => get("/analytics/products", r),
  operations: (r?: Range & { page?: number }) => get("/analytics/operations", r),
  retention: () => get("/analytics/retention"),
  forecast: () => get("/analytics/forecast"),
  reportSummary: (r?: Range) => get("/reports/summary", r),
  chat: (message: string, session_id: string) => http.post<ChatResponse>("/chat", { message, session_id }).then((r) => r.data),
  history: (session_id: string) => get("/chat/history", { session_id }),
  clearHistory: (session_id: string) => http.delete("/chat/history", { params: { session_id } }).then((r) => r.data),
  downloadReport: async (format: "pdf" | "csv" | "md", range: Range, ai: boolean) => {
    const res = await http.post("/reports/generate", { format, ...clean(range), include_ai_narrative: ai }, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a"); a.href = url; a.download = `ecommerce360_summary.${format}`; a.click(); URL.revokeObjectURL(url);
  },
};

export function errorMessage(e: any): string {
  if (e?.response?.status === 429) return "Too many requests - please wait a moment.";
  if (e?.response?.status === 401) return "Unauthorized: check VITE_API_KEY.";
  if (e?.response?.data?.detail && typeof e.response.data.detail === "string") return e.response.data.detail;
  if (e?.code === "ERR_NETWORK" || !e?.response) return "Cannot reach the backend. Is it running on port 8000?";
  return "Something went wrong. Please try again.";
}
