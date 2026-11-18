"""Orchestrates: question -> plan (LLM or offline) -> guard -> read-only execution -> grounded answer."""
from __future__ import annotations

import logging
import re
import time
import uuid

from ..analytics.insights import build_insights
from ..analytics.service import Analytics, clean
from ..core.config import Settings
from ..database.executor import Executor
from . import fallback
from .chat_store import ChatStore
from .sql_guard import enforce_limit, validate

log = logging.getLogger("ecom360.analyst")
PREVIEW_ROWS = 50
NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*([MmKk]\b)?")


def build_chart(rows: list[dict], spec: dict | None) -> dict | None:
    """Chart values are copied from result rows; the model only picks which columns to plot."""
    if not rows or not spec or not isinstance(spec, dict):
        return None
    x, y, typ = spec.get("x"), spec.get("y"), spec.get("type", "bar")
    if typ not in ("bar", "line", "pie") or x not in rows[0] or y not in rows[0]:
        return None
    if not all(isinstance(r[y], (int, float)) or r[y] is None for r in rows):
        return None
    return {"type": typ, "x": x, "y": y, "data": [{x: r[x], y: r[y]} for r in rows[:30]]}


def ungrounded_numbers(answer: str, rows: list[dict]) -> list[str]:
    """Numbers in the narrative that cannot be traced to a result value (heuristic safety net)."""
    vals: set[float] = set()
    for r in rows:
        for v in r.values():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                vals.add(float(v))
            elif isinstance(v, str):
                vals.update(float(t) for t in re.findall(r"\d+(?:\.\d+)?", v))
    cands: list[float] = []
    for v in vals:
        cands += [v, v / 1e3, v / 1e6, v * 100 if abs(v) <= 1.5 else v]
    totals = [sum(float(r[k]) for r in rows if isinstance(r.get(k), (int, float))) for k in (rows[0] if rows else [])]
    cands += totals + [t / 1e6 for t in totals] + [t / 1e3 for t in totals] + [float(len(rows))]
    bad = []
    for m in NUM_RE.finditer(answer):
        raw = m.group(1).replace(",", "")
        x = float(raw)
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        if x <= 10 and x == int(x):
            continue                      # ranks / small counts ("top 5")
        if 2015 <= x <= 2019 and x == int(x):
            continue                      # years
        if not any(abs(x - c) <= 0.5 * 10 ** (-decimals) + 1e-6 for c in cands):
            bad.append(m.group(0).strip())
    return bad


class Analyst:
    def __init__(self, ex: Executor, settings: Settings, llm=None, store: ChatStore | None = None):
        self.ex, self.s, self.llm = ex, settings, llm
        self.store = store or ChatStore(ex)
        self.analytics = Analytics(ex)

    @property
    def mode(self) -> str:
        return "llm" if self.llm else "offline"

    # ------------------------------------------------------------------------------------------
    def answer(self, message: str, session_id: str | None = None) -> dict:
        sid = session_id or uuid.uuid4().hex
        history = self.store.history(sid, limit=self.s.chat_history_turns * 2)
        self.store.add(sid, "user", message)
        result = self._answer(message, sid, history)
        result["session_id"] = sid
        meta = {k: result.get(k) for k in ("sql", "chart", "status", "mode", "calculation", "data_source", "followups",
                                            "row_count", "warnings", "focus")}
        meta["rows"] = result.get("rows", [])[:PREVIEW_ROWS]
        self.store.add(sid, "assistant", result["answer"], meta)
        return result

    def _base(self, status, answer, **kw) -> dict:
        d = {"status": status, "answer": answer, "mode": self.mode, "sql": None, "tables": [], "rows": [], "row_count": 0,
             "chart": None, "calculation": None, "data_source": None, "followups": [], "warnings": [], "focus": None,
             "llm_unavailable_reason": None if self.llm else "OPENAI_API_KEY is not configured; running in offline mode."}
        d.update(kw)
        return d

    def _answer(self, question: str, sid: str, history: list[dict]) -> dict:
        # 1) plan -----------------------------------------------------------------------------
        try:
            if self.llm:
                plan = self.llm.plan(question, history)
            else:
                p = fallback.match(question, history, self.s.currency_symbol)
                if p is None:
                    return self._base("unsupported", fallback.HELP,
                                      followups=["What is total revenue?", "Which categories are performing best?"])
                if p.intent == "insights":
                    return self._insights_answer()
                if p.sql is None:
                    return self._base(p.status, p.message or "", followups=p.followups)
                plan = {"intent": "sql", "sql": p.sql, "chart": p.chart, "calculation": p.calc, "followups": p.followups,
                        "_narrate": p.narrate, "_focus": p.focus}
        except Exception as exc:  # network/API problems must not leak internals
            log.error("planning failed: %s", type(exc).__name__)  # never log message text (may echo key fragments)
            return self._base("error", "The AI service could not be reached or returned an error. "
                                       "Check the API key/model and try again.", warnings=[type(exc).__name__])

        intent = plan.get("intent")
        if intent != "sql" or not plan.get("sql"):
            return self._base("unsupported" if intent == "unsupported" else "ok",
                              plan.get("message") or "I can't answer that from the available data.",
                              followups=plan.get("followups") or [])

        # 2) guard (+ one repair attempt for LLM SQL) -----------------------------------------------
        sql = plan["sql"]
        g = validate(sql)
        if not g.ok and self.llm:
            self.store.log_query(sid, question, sql, None, "rejected", g.reason, 0, 0, self.mode)
            try:
                plan2 = self.llm.repair(question, history, sql, g.reason)
                if plan2.get("intent") == "sql" and plan2.get("sql"):
                    plan, sql = plan2, plan2["sql"]
                    g = validate(sql)
            except Exception as exc:
                log.error("repair failed: %s", type(exc).__name__)
        if not g.ok:
            self.store.log_query(sid, question, sql, None, "rejected", g.reason, 0, 0, self.mode)
            return self._base("rejected", "I couldn't produce a query that passes the safety checks, so nothing was run. "
                                          f"Reason: {g.reason}", sql=sql, warnings=["sql_rejected"])

        # 3) execute read-only with limits ----------------------------------------------------------
        final_sql = enforce_limit(g.sql, self.s.ai_row_limit)
        t0 = time.time()
        try:
            rows = [{k: clean(v) for k, v in r.items()} for r in self.ex.query_readonly(final_sql, self.s.ai_statement_timeout_ms)]
        except Exception as exc:
            log.warning("query failed: %s", type(exc).__name__)
            self.store.log_query(sid, question, sql, final_sql, "error", type(exc).__name__, 0, int((time.time() - t0) * 1000), self.mode)
            return self._base("error", "The query could not be executed (it may have timed out or referenced something that "
                                       "doesn't exist). Try rephrasing the question.", sql=g.sql, tables=g.tables)
        ms = int((time.time() - t0) * 1000)
        self.store.log_query(sid, question, sql, final_sql, "ok", None, len(rows), ms, self.mode)
        common = dict(sql=g.sql, tables=g.tables, rows=rows[:PREVIEW_ROWS], row_count=len(rows), calculation=plan.get("calculation"),
                      data_source=", ".join(f"analytics.{t}" for t in g.tables), followups=(plan.get("followups") or [])[:3])
        if len(rows) >= self.s.ai_row_limit:
            common["warnings"] = [f"Result truncated at {self.s.ai_row_limit} rows."]
        if not rows:
            return self._base("no_data", "The query ran successfully but returned no rows, so there is no data to report.", **common)

        # 4) grounded narration ---------------------------------------------------------------------
        warnings = list(common.get("warnings", []))
        try:
            if self.llm:
                text = self.llm.narrate(question, g.sql, rows, plan.get("calculation") or "")
            else:
                text = plan["_narrate"](rows) if plan.get("_narrate") else f"Query returned {len(rows)} rows."
        except Exception as exc:
            log.error("narration failed: %s", type(exc).__name__)
            text = f"The query returned {len(rows)} row(s); the explanation service failed, so only the raw result is shown."
            warnings.append("narration_failed")
        if self.llm:
            bad = ungrounded_numbers(text, rows)
            if bad:
                warnings.append("Some numbers in the explanation could not be matched to the query result: "
                                + ", ".join(bad[:6]) + ". Verify against the table.")
        common["warnings"] = warnings
        focus = plan.get("_focus")
        first = rows[0]
        if not focus and isinstance(first.get("category"), str):
            focus = {"category": first["category"]}
        common["focus"] = focus
        return self._base("ok", text, chart=build_chart(rows, plan.get("chart")), **common)

    def _insights_answer(self) -> dict:
        ins = build_insights(self.analytics, cur=self.s.currency_symbol)
        obs = [i for i in ins if i["type"] == "observation"]
        rec = [i for i in ins if i["type"] == "recommendation"]
        txt = "**Observations (calculated from the data)**\n" + "\n".join(f"- **{i['title']}:** {i['text']}" for i in obs)
        txt += "\n\n**Recommendations (suggestions, not data results)**\n" + "\n".join(f"- **{i['title']}:** {i['text']}" for i in rec)
        return self._base("ok", txt, data_source="analytics views (see each insight's basis)",
                          calculation="; ".join(f"{i['title']}: {i['basis']}" for i in ins),
                          followups=["Which categories are performing best?", "Identify our delivery problems."])
