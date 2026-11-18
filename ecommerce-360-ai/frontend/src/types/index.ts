export interface ChatMeta {
  sql?: string | null; chart?: ChartSpec | null; rows?: Record<string, any>[]; row_count?: number;
  status?: string; mode?: string; calculation?: string | null; data_source?: string | null;
  followups?: string[]; warnings?: string[]; llm_unavailable_reason?: string | null;
}
export interface ChartSpec { type: "bar" | "line" | "pie"; x: string; y: string; data: Record<string, any>[] }
export interface ChatMessage extends ChatMeta { role: "user" | "assistant"; content: string; id: string }
export interface ChatResponse extends ChatMeta { answer: string; session_id: string }
export type Range = { start?: string; end?: string };
