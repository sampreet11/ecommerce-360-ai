"""Conversation memory + SQL audit log, stored in PostgreSQL (app.chat_messages / app.query_log)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from ..database.executor import Executor


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ChatStore:
    def __init__(self, ex: Executor):
        self.ex = ex

    def add(self, session_id: str, role: str, content: str, metadata: dict | None = None) -> str:
        mid = uuid.uuid4().hex
        self.ex.execute(
            "INSERT INTO app.chat_messages (id, session_id, role, content, metadata_json, created_at) "
            "VALUES (:id, :s, :r, :c, :m, :t)",
            {"id": mid, "s": session_id, "r": role, "c": content,
             "m": json.dumps(metadata, default=str) if metadata else None, "t": _now()})
        return mid

    def history(self, session_id: str, limit: int = 50) -> list[dict]:
        rows = self.ex.query(
            "SELECT id, role, content, metadata_json, created_at FROM app.chat_messages "
            "WHERE session_id = :s ORDER BY created_at DESC, id DESC LIMIT :n", {"s": session_id, "n": limit})
        out = []
        for r in reversed(rows):
            out.append({"id": r["id"], "role": r["role"], "content": r["content"],
                        "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else None,
                        "created_at": str(r["created_at"])})
        return out

    def clear(self, session_id: str) -> int:
        n = self.ex.query("SELECT COUNT(*) AS n FROM app.chat_messages WHERE session_id = :s", {"s": session_id})[0]["n"]
        self.ex.execute("DELETE FROM app.chat_messages WHERE session_id = :s", {"s": session_id})
        return int(n)

    def log_query(self, session_id, question, generated_sql, executed_sql, status, reason, row_count, duration_ms, mode):
        self.ex.execute(
            "INSERT INTO app.query_log (id, session_id, question, generated_sql, executed_sql, status, rejection_reason, "
            "row_count, duration_ms, mode, created_at) VALUES (:id,:s,:q,:g,:e,:st,:r,:n,:d,:m,:t)",
            {"id": uuid.uuid4().hex, "s": session_id, "q": (question or "")[:1000], "g": generated_sql, "e": executed_sql,
             "st": status, "r": reason, "n": row_count, "d": duration_ms, "m": mode, "t": _now()})
