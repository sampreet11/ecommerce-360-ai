"""Defence-in-depth validation of model-generated SQL.

Layers: (1) this tokenizer-based validator (no regex-on-strings tricks: comments, dollar
quotes and double-quoted identifiers are rejected outright), (2) a relation/column
allow-list, (3) a forced outer LIMIT, (4) a read-only DB transaction with a statement
timeout on a restricted role (see database/executor.py and scripts/db_roles.sql).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .catalog import ALLOWED, COLUMNS, SCHEMA

MAX_SQL_CHARS = 4000

FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke", "copy", "call",
    "do", "execute", "set", "reset", "vacuum", "analyze", "merge", "into", "lock", "listen", "notify",
    "begin", "commit", "rollback", "savepoint", "declare", "fetch", "prepare", "deallocate", "comment",
    "refresh", "reindex", "cluster", "attach", "detach", "pragma", "load", "import", "returning",
    "recursive", "show", "explain", "security", "owner", "vacuum", "abort", "start", "checkpoint",
}
FORBIDDEN_FUNCS = {"pg_sleep", "set_config", "current_setting", "dblink", "version", "current_user",
                   "session_user", "inet_server_addr", "query_to_xml", "xpath", "txid_current"}
FORBIDDEN_NAMES = {"information_schema", "pg_catalog", "pg_class", "pg_user", "pg_shadow", "pg_roles",
                   "sqlite_master", "sqlite_schema"}
NOT_ALIAS = {"where", "group", "order", "join", "inner", "left", "right", "full", "cross", "on", "using",
             "limit", "union", "having", "natural", "lateral", "window", "offset", "except", "intersect",
             "outer", "as", "select", "from"}
FROM_FUNCS = {"extract", "substring", "trim", "overlay", "position"}

TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)
  | (?P<str>'(?:[^']|'')*')
  | (?P<num>\d+(?:\.\d+)?)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op><>|<=|>=|!=|\|\||::|[-+*/%=<>(),.;])
""", re.X)


@dataclass
class GuardResult:
    ok: bool
    sql: str = ""
    reason: str = ""
    tables: list[str] = field(default_factory=list)


def tokenize(sql: str) -> list[tuple[str, str]]:
    toks, pos = [], 0
    while pos < len(sql):
        m = TOKEN_RE.match(sql, pos)
        if not m:
            raise ValueError(f"unsupported character {sql[pos]!r} at position {pos}")
        pos = m.end()
        if m.lastgroup != "ws":
            toks.append((m.lastgroup, m.group()))
    return toks


def _reject(reason: str) -> GuardResult:
    return GuardResult(False, reason=reason)


def validate(sql: str) -> GuardResult:
    if not sql or not sql.strip():
        return _reject("Empty query.")
    sql = sql.strip()
    if len(sql) > MAX_SQL_CHARS:
        return _reject("Query too long.")
    if "--" in sql or "/*" in sql or "*/" in sql:
        return _reject("SQL comments are not allowed.")
    if "$" in sql or '"' in sql or "`" in sql or "\\" in sql:
        return _reject("Quoted identifiers, dollar quoting and backslashes are not allowed.")
    try:
        toks = tokenize(sql)
    except ValueError as e:
        return _reject(str(e))

    # single statement
    semis = [i for i, (_, v) in enumerate(toks) if v == ";"]
    if semis:
        if semis != [len(toks) - 1]:
            return _reject("Multiple statements are not allowed.")
        toks = toks[:-1]
        sql = sql.rstrip().rstrip(";").rstrip()
    if not toks:
        return _reject("Empty query.")

    low = [(k, v.lower()) for k, v in toks]
    if low[0][1] not in ("select", "with"):
        return _reject("Only SELECT queries (optionally starting with WITH) are allowed.")

    for i, (k, v) in enumerate(low):
        if k != "ident":
            continue
        nxt = low[i + 1][1] if i + 1 < len(low) else ""
        if v == "replace" and nxt == "(":
            continue  # string function REPLACE(...)
        if v in FORBIDDEN_KEYWORDS:
            return _reject(f"Keyword '{v.upper()}' is not allowed (read-only SELECT queries only).")
        if v in FORBIDDEN_NAMES or v.startswith("pg_") or v.startswith("lo_"):
            return _reject(f"Access to '{v}' is not allowed.")
        if nxt == "(" and v in FORBIDDEN_FUNCS:
            return _reject(f"Function '{v}' is not allowed.")

    # CTE names:  name AS (    or   name (cols) AS (  -- only the first form is supported
    ctes = {low[i][1] for i in range(len(low) - 2)
            if low[i][0] == "ident" and low[i + 1][1] == "as" and low[i + 2][1] == "(" and low[i][1] not in NOT_ALIAS}

    # relations
    aliases: dict[str, str] = {}
    tables: list[str] = []
    paren_stack: list[str] = []
    i, n = 0, len(low)

    def read_relation(j: int):
        """parse relation starting at j; returns (next index, error)"""
        if j >= n:
            return j, "Incomplete FROM clause."
        if low[j][1] == "(":
            return j, None  # subquery: contents scanned by the main loop
        if low[j][0] != "ident":
            return j, "Unsupported FROM clause."
        parts = [low[j][1]]
        j += 1
        while j + 1 < n and low[j][1] == "." and low[j + 1][0] == "ident":
            parts.append(low[j + 1][1]); j += 2
        if len(parts) > 2:
            return j, "Invalid relation name."
        if len(parts) == 2 and parts[0] != SCHEMA:
            return j, f"Schema '{parts[0]}' is not allowed."
        table = parts[-1]
        is_cte = len(parts) == 1 and table in ctes
        if not is_cte and table not in ALLOWED:
            return j, f"Table or view '{table}' is not approved. Approved: {', '.join(ALLOWED)}."
        alias = table
        if j < n and low[j][1] == "as" and j + 1 < n and low[j + 1][0] == "ident":
            alias = low[j + 1][1]; j += 2
        elif j < n and low[j][0] == "ident" and low[j][1] not in NOT_ALIAS:
            alias = low[j][1]; j += 1
        if not is_cte:
            aliases[alias] = table
            aliases.setdefault(table, table)
            if table not in tables:
                tables.append(table)
        else:
            aliases[alias] = "__cte__"
        return j, None

    while i < n:
        k, v = low[i]
        if v == "(":
            paren_stack.append(low[i - 1][1] if i > 0 and low[i - 1][0] == "ident" else "")
        elif v == ")":
            if paren_stack:
                paren_stack.pop()
        elif k == "ident" and v in ("from", "join"):
            if v == "from" and paren_stack and paren_stack[-1] in FROM_FUNCS:
                i += 1
                continue
            j, err = read_relation(i + 1)
            if err:
                return _reject(err)
            while v == "from" and j < n and low[j][1] == ",":
                j, err = read_relation(j + 1)
                if err:
                    return _reject(err)
            i = max(j, i + 1)
            continue
        i += 1

    if not tables and not ctes:
        return _reject("Query must read from an approved table or view.")

    # qualified column validation: alias.column
    for i in range(n - 2):
        if low[i][0] == "ident" and low[i + 1][1] == "." and low[i + 2][1] not in ("*",):
            tbl = aliases.get(low[i][1])
            if tbl and tbl != "__cte__" and low[i + 2][0] == "ident":
                if low[i + 2][1] not in COLUMNS[tbl]:
                    return _reject(f"Column '{low[i + 2][1]}' does not exist in '{tbl}'. "
                                   f"Available: {', '.join(sorted(COLUMNS[tbl]))}.")
    return GuardResult(True, sql=sql, tables=tables)


def enforce_limit(sql: str, limit: int) -> str:
    """Wrap a validated query so the DB can never return more than `limit` rows."""
    return f"SELECT * FROM ({sql}) AS guarded_q LIMIT {int(limit)}"
