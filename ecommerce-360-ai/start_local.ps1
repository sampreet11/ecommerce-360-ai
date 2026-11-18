# No-Docker path: requires local PostgreSQL 16 (db "ecommerce360", user "ecom"), Python 3.12, Node 20.
# Usage:  powershell -ExecutionPolicy Bypass -File start_local.ps1
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env - edit it, then re-run." }
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([^#=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim()) } }
py -m venv backend\.venv
& backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
Push-Location backend
& .venv\Scripts\python -m app.database.setup
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$PWD'; .venv\Scripts\python -m uvicorn app.main:app --port 8000"
Pop-Location
Push-Location frontend; npm install; Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$PWD'; npm run dev"; Pop-Location
Write-Host "Frontend: http://localhost:5173   API docs: http://localhost:8000/docs"
