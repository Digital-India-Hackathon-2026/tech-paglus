#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/frontend"
if [ ! -f .env.local ]; then
  cp .env.local.example .env.local
fi
npm install
npm run dev
