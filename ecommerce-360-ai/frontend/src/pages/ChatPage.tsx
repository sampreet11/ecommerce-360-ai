import { useEffect, useRef, useState } from "react";
import { Send, Trash2 } from "lucide-react";
import { api, errorMessage } from "../services/api";
import ChatBubble from "../components/ChatBubble";
import { Note } from "../components/ui";
import type { ChatMessage } from "../types";

const WELCOME = "Hello! I'm your E-Commerce AI Business Analyst. Ask me anything about sales, customers, products, delivery performance, and business trends.";
const PROMPTS = ["Analyse our overall revenue.", "Which categories are performing best?", "Identify our delivery problems.", "Analyse repeat customers.", "Give me three important business recommendations."];

const sessionId = () => {
  let s = localStorage.getItem("ecom360_session");
  if (!s) { s = (crypto.randomUUID?.() ?? String(Date.now())).replace(/[^A-Za-z0-9_-]/g, ""); localStorage.setItem("ecom360_session", s); }
  return s;
};

export default function ChatPage() {
  const [sid, setSid] = useState(sessionId);
  const [msgs, setMsgs] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [offlineReason, setOfflineReason] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.history(sid).then((h) => setMsgs(h.messages.map((m: any) => ({ role: m.role, content: m.content, id: m.id, ...(m.metadata ?? {}) })))).catch(() => {});
    api.status().then((s) => setOfflineReason(s.ai_mode === "offline" ? "AI is in offline mode: OPENAI_API_KEY is not configured, so only a fixed set of questions is supported." : null)).catch(() => {});
  }, [sid]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setInput(""); setBusy(true);
    setMsgs((m) => [...m, { role: "user", content: q, id: `u${Date.now()}` }]);
    try {
      const r = await api.chat(q, sid);
      setMsgs((m) => [...m, { role: "assistant", content: r.answer, id: `a${Date.now()}`, ...r }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "assistant", content: errorMessage(e), id: `e${Date.now()}`, status: "error" }]);
    } finally { setBusy(false); }
  }
  async function clear() {
    await api.clearHistory(sid).catch(() => {});
    setMsgs([]);
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-7rem)] max-w-4xl flex-col lg:h-[calc(100vh-4rem)]">
      <div className="mb-3 flex items-center justify-between">
        <div><h1 className="text-xl font-semibold text-slate-900">AI Business Analyst</h1><p className="text-xs text-slate-500">Answers are computed from the database with read-only SQL you can inspect.</p></div>
        <button onClick={clear} className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100"><Trash2 size={13} />Clear</button>
      </div>
      {offlineReason && <div className="mb-3"><Note>{offlineReason}</Note></div>}
      <div className="flex-1 space-y-4 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-4">
        <ChatBubble m={{ role: "assistant", content: WELCOME, id: "welcome" }} onFollowup={send} />
        {msgs.length === 0 && <div className="flex flex-wrap gap-2 pl-0 sm:pl-9">{PROMPTS.map((p) => <button key={p} onClick={() => send(p)} className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 hover:border-brand-500 hover:text-brand-700">{p}</button>)}</div>}
        {msgs.map((m) => <ChatBubble key={m.id} m={m} onFollowup={send} />)}
        {busy && <div className="flex items-center gap-1 pl-0 sm:pl-9" aria-label="Thinking">{[0, 1, 2].map((i) => <span key={i} className="dot h-2 w-2 rounded-full bg-brand-500" style={{ animationDelay: `${i * 0.15}s` }} />)}</div>}
        <div ref={end} />
      </div>
      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="mt-3 flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)} maxLength={1000} placeholder="Ask about revenue, categories, delivery, customers..." className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
        <button disabled={busy || !input.trim()} className="flex items-center gap-1 rounded-xl bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"><Send size={15} /><span className="hidden sm:inline">Send</span></button>
      </form>
    </div>
  );
}
