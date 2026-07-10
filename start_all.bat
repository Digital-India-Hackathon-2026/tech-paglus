@echo off
setlocal

set "ROOT_DIR=%~dp0"

REM ---- Backend setup ----
cd /d "%ROOT_DIR%backend"

if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

pip install -r requirements.txt

if not exist .env (
    copy .env.example .env
)

for /f "tokens=5" %%p in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%p 2>nul
)

REM Start backend in a new window so this script can continue to the frontend
start "AgriSarthi Backend" cmd /k "cd /d %ROOT_DIR%backend && call .venv\Scripts\activate.bat && python -m uvicorn main:app --reload --reload-exclude "".venv/*"" --host 127.0.0.1 --port 8000"

REM ---- Frontend setup ----
cd /d "%ROOT_DIR%frontend"

if not exist .env.local (
    copy .env.local.example .env.local
)

call npm install
call npm run dev

endlocal
