@echo off
setlocal

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%frontend"

if not exist .env.local (
    copy .env.local.example .env.local
)

call npm install
call npm run dev

endlocal
