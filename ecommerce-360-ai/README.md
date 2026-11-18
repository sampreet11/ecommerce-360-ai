# E-Commerce 360° AI Intelligence Platform

Full-stack BI + Generative AI app on the Olist Brazilian e-commerce dataset. Extends the original SQL / Python / Excel / Power BI
project (all preserved in `SQL/`, `Python/`, `Excel/`, `PowerBI/`, `Charts/`; old prototype in `legacy/`).

**Stack:** React + TypeScript + Vite + Tailwind + Recharts · FastAPI · PostgreSQL (SQL views) · Alembic · OpenAI API · Docker Compose

## Features
Executive dashboard · Sales / Customer (RFM, cohorts) / Product / Operations analytics · AI analyst (NL→SQL, grounded answers,
inspectable SQL, charts, follow-ups, persistent memory) · PDF/CSV/Markdown reports · offline mode without an API key.

## Run on Windows (Docker Desktop)
```powershell
# 1. extract the ZIP, open PowerShell in the folder
copy .env.example .env        # then put your OPENAI_API_KEY in .env (optional: works offline without it)
.\start_project.bat           # first start builds images and imports ~110k rows (1-3 min)
# open http://localhost:8080   (API docs: http://localhost:8000/docs)
.\stop_project.bat
```
Logs: `docker compose logs -f backend`. Reset data: `docker compose down -v`.
**Without Docker:** install PostgreSQL 16 (create user `ecom`, db `ecommerce360`), Python 3.12, Node 20, then
`powershell -ExecutionPolicy Bypass -File start_local.ps1`.

Troubleshooting: *port 5432/8000/8080 busy* → stop the other service or edit `docker-compose.yml`; *"Cannot reach the backend"* → check
`docker compose ps`; *AI says offline mode* → key missing/placeholder in `.env`, then `docker compose up -d --build backend`.

## Tests
`cd backend; python -m unittest discover -s tests -t .` (47 tests; use `pytest` if installed). See "Verification".

## Verification - what was and was NOT executed
Executed (in the build sandbox): 47 backend unit/integration tests, using SQLite as a stand-in for PostgreSQL, loaded with the real
CSVs: KPI reconciliation vs independent pandas calculations and the original `monthly_kpis`/`category_kpis`/forecast CSVs; SQL guard
(accept/reject cases); analyst flow with a scripted fake LLM; offline mode; memory; report PDF/CSV/MD generation; read-only enforcement.
Syntax-only parse of the 19 frontend files.
**Not executed** (no network/Docker/Postgres there): live OpenAI calls; PostgreSQL itself (migrations, `ai_readonly` role, `SET TRANSACTION`);
FastAPI endpoints (framework not installable); `npm install`, TypeScript type-check, Vite build; Docker builds. Expect to fix small
issues on first run; please run the steps above and report errors.

## Data limitations
No cost/profit/discount data; revenue ≠ profit. Reviews, payments, raw orders were not in the supplied ZIP, so review analytics are
reported as unavailable. Data is historical (Sep 2016-Sep 2018). Repeat purchasing ≠ subscription churn. Forecast is a rolling-mean baseline.
Original README figures differ from recomputed values - see `docs/data-dictionary.md`.

## Security (local demo)
Secrets via `.env` (git-ignored); AI SQL guarded + read-only role; rate limiting; CORS allow-list; generic error responses; optional shared API key.
Not production-ready: no user accounts, in-memory rate limiter, default DB passwords in `.env.example`, no TLS.

## Docs
`docs/architecture.md` (diagrams) · `ai-system.md` · `api-documentation.md` · `data-dictionary.md` · `interview-guide.md`

## Repo description
"Full-stack BI platform on the Olist dataset: React dashboards + FastAPI + PostgreSQL, with an LLM analyst that turns questions into validated read-only SQL."

## Suggested commits
1. chore: preserve original analytics project  2. feat(db): schema, views, loader, migration  3. feat(api): analytics service + endpoints
4. feat(ai): SQL guard, analyst, offline mode  5. feat(web): React dashboard and chat  6. chore: docker, scripts, docs  7. test: reconciliation + safety suites

## Future work
Reviews/payments tables · streaming answers · real auth · CI · semantic layer · screenshots (`Screenshots/`).
