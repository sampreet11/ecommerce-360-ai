"""OpenAI wrapper (official SDK, Chat Completions). Only this module talks to the API.

The model never receives credentials, env vars or DB connection strings; it receives the
approved schema text, short conversation history and (for narration) query RESULT rows.
"""
from __future__ import annotations

import json
import logging
from typing import Protocol

from .catalog import METRIC_RULES, schema_prompt

log = logging.getLogger("ecom360.llm")

PLAN_SYSTEM = """You are the query planner of an e-commerce business-intelligence assistant.
Convert the user's question into ONE read-only SQL query (PostgreSQL syntax) over the approved relations below.

APPROVED RELATIONS (use only these tables/columns; unqualified names are fine):
{schema}

{rules}
SQL rules: a single SELECT (optionally with WITH); no comments; no semicolons inside; no INSERT/UPDATE/DELETE/DDL;
alias every computed column; always ORDER BY for rankings; include LIMIT for lists (<= 50).
For percentages return the percentage number (e.g. 8.11) in a column named *_pct.
Resolve pronouns ("it", "that category") from the conversation history.

Reply with a JSON object only:
{{"intent": "sql" | "unsupported" | "chitchat",
  "sql": "<query or null>",
  "message": "<for unsupported/chitchat: short helpful reply, else null>",
  "calculation": "<one or two sentences describing how the metric is calculated>",
  "chart": null | {{"type": "bar"|"line"|"pie", "x": "<result column>", "y": "<numeric result column>"}},
  "followups": ["<up to 3 short follow-up questions>"]}}
Use "unsupported" when the data cannot answer (reviews, payments, profit, margin, discounts, live data)."""

NARRATE_SYSTEM = """You are a careful business analyst. Write the answer to the user's question using ONLY the numbers
present in RESULT_JSON (the database output). Rules:
- Never introduce a number that is not in RESULT_JSON, except trivial arithmetic on it (state it clearly as a calculation).
- Revenue means item price excluding freight; never call it profit. Data is historical (2016-2018), not live.
- Separate: **Verified result**, then **Interpretation** (hedged; correlation is not causation) and, only if asked for advice,
  **Recommendations**. Keep it concise, use Markdown, format money with the R$ symbol.
- If the result is empty or does not answer the question, say so plainly."""


class LLM(Protocol):
    def plan(self, question: str, history: list[dict]) -> dict: ...
    def repair(self, question: str, history: list[dict], bad_sql: str, error: str) -> dict: ...
    def narrate(self, question: str, sql: str, rows: list[dict], calculation: str) -> str: ...


class OpenAILLM:
    def __init__(self, api_key: str, model: str, timeout: float = 45.0):
        from openai import OpenAI  # official SDK
        self.client = OpenAI(api_key=api_key, timeout=timeout)
        self.model = model

    def _history_messages(self, history: list[dict]) -> list[dict]:
        msgs = []
        for m in history:
            content = m["content"]
            sql = (m.get("metadata") or {}).get("sql")
            if m["role"] == "assistant" and sql:
                content += f"\n\n[SQL used earlier: {sql}]"
            msgs.append({"role": m["role"], "content": content[:2500]})
        return msgs

    def _plan_call(self, messages: list[dict]) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model, temperature=0, response_format={"type": "json_object"}, messages=messages)
        try:
            return json.loads(resp.choices[0].message.content)
        except (json.JSONDecodeError, TypeError):
            return {"intent": "unsupported", "message": "I couldn't interpret the planning response. Please rephrase."}

    def plan(self, question, history):
        system = PLAN_SYSTEM.format(schema=schema_prompt(), rules=METRIC_RULES)
        return self._plan_call([{"role": "system", "content": system}, *self._history_messages(history),
                                {"role": "user", "content": question}])

    def repair(self, question, history, bad_sql, error):
        system = PLAN_SYSTEM.format(schema=schema_prompt(), rules=METRIC_RULES)
        return self._plan_call([
            {"role": "system", "content": system}, *self._history_messages(history),
            {"role": "user", "content": question},
            {"role": "assistant", "content": json.dumps({"intent": "sql", "sql": bad_sql})},
            {"role": "user", "content": f"That query was rejected: {error}\nReturn a corrected JSON plan."}])

    def narrate(self, question, sql, rows, calculation):
        payload = json.dumps({"RESULT_JSON": rows[:50], "row_count": len(rows), "calculation": calculation}, default=str)
        resp = self.client.chat.completions.create(
            model=self.model, temperature=0.2,
            messages=[{"role": "system", "content": NARRATE_SYSTEM},
                      {"role": "user", "content": f"Question: {question}\nSQL executed: {sql}\n{payload}"}])
        return (resp.choices[0].message.content or "").strip()
