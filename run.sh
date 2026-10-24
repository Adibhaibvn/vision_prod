#!/usr/bin/env bash
# Vision-to-Cart — one-command local run.
set -euo pipefail

cd "$(dirname "$0")/backend"

if [ ! -d .venv ]; then
  echo "==> creating virtualenv"
  PYTHON_BIN=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3)
  "$PYTHON_BIN" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> installing dependencies"
pip install -q --upgrade pip
pip install -q -r requirements.txt

if [ ! -f .env ]; then
  echo "==> no .env found — copying .env.example (demo mode)"
  cp .env.example .env
fi

echo "==> starting server on http://localhost:8000"
exec uvicorn app.main:app --reload --port 8000
