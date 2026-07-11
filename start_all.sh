#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$ROOT_DIR/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
fi
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
python -m uvicorn main:app --reload --reload-exclude ".venv/*" --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT

cd "$ROOT_DIR/frontend"
if [ ! -f .env.local ]; then
  cp .env.local.example .env.local
fi
npm install
npm run dev
