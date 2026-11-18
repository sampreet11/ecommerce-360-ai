@echo off
REM Starts PostgreSQL + backend + frontend with Docker Compose.
where docker >nul 2>nul || (echo Docker Desktop is not installed or not on PATH. See README "Without Docker". & exit /b 1)
if not exist .env (copy .env.example .env >nul & echo Created .env from .env.example - add your OPENAI_API_KEY to enable the LLM, then re-run.)
docker compose up --build -d
if errorlevel 1 (echo Docker Compose failed. Is Docker Desktop running? & exit /b 1)
echo.
echo First start imports ~110k rows; watch progress with:  docker compose logs -f backend
echo App:      http://localhost:8080
echo API docs: http://localhost:8000/docs
echo Stop with stop_project.bat
