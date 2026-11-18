# API (full interactive docs: http://localhost:8000/docs)
Filters `start`/`end` = purchase month (YYYY-MM-DD, inclusive). `X-API-Key` required only if `APP_API_KEY` is set.

| Method | Path | Notes |
|---|---|---|
| GET | /api/health | liveness |
| GET | /api/system/status | DB status, row counts, coverage, AI mode (no secrets) |
| GET | /api/dashboard/overview, revenue-trend, top-categories, delivery-performance, customer-metrics, review-analysis | review-analysis returns `available:false` |
| GET | /api/analytics/sales, customers, products, operations, retention, forecast | products/operations: `page`, `page_size`, `sort` |
| POST | /api/chat | `{message, session_id}` -> answer, sql, rows, chart, followups, warnings, status |
| GET/DELETE | /api/chat/history?session_id= | memory |
| GET | /api/reports/summary | JSON |
| POST | /api/reports/generate | `{format: pdf|csv|md, start, end, include_ai_narrative}` -> file |
Chat is rate-limited more strictly than other routes (in-memory, single process).
