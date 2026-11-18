# AI system

**Grounding.** The LLM never produces numbers. It (1) plans a SQL query, (2) later writes prose from the returned rows.
Charts are built by the backend from result rows (the model only names the x/y columns). After narration the backend extracts
numbers from the prose and flags any not traceable to the result (`warnings`) - a heuristic, not a proof.

**SQL safety layers** (`app/ai/sql_guard.py`, `database/executor.py`, `database/setup.py`)
1. Tokenizer-based validation: one statement; starts with SELECT/WITH; comments, `$`-quotes, quoted identifiers rejected;
   keyword blacklist (INSERT/UPDATE/DELETE/DDL/COPY/INTO/RETURNING/RECURSIVE...); dangerous functions (pg_sleep...) and
   `pg_*`/`information_schema` rejected.
2. Allow-list of 12 views/tables and their columns (`app/ai/catalog.py`); `alias.column` references are verified.
3. Forced outer `LIMIT` (default 500).
4. Execution as the `ai_readonly` PostgreSQL role (SELECT only on the allow-list, no access to schema `app`), inside
   `SET TRANSACTION READ ONLY` with `statement_timeout`.
5. Failed validation triggers one LLM repair attempt with the error, then a refusal. Every attempt is logged in `app.query_log`
   (no secrets).
Limits: unqualified column typos are caught by the database, not the validator; a blacklist/tokenizer is not a full SQL parser.

**Memory.** Last N messages (with previous SQL) are sent to the model; the offline mode keeps a `focus` entity (e.g. category)
in message metadata so "How much did it generate?" resolves. Memory never replaces query results.

**Missing key / API failure.** `llm_configured` false -> offline mode with an explicit banner; API exceptions return a generic
error (only the exception class is logged, because provider error text can echo key fragments).
