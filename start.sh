#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"

# --- Locate the backend virtual environment (setup.sh creates .venv) ---
if [ -d "$BACKEND_DIR/.venv" ]; then
  VENV_DIR="$BACKEND_DIR/.venv"
elif [ -d "$BACKEND_DIR/venv" ]; then
  VENV_DIR="$BACKEND_DIR/venv"
else
  echo "No backend virtual environment found."
  echo "Run the one-time setup first:"
  echo "  cd backend && ./setup.sh"
  exit 1
fi

# --- Require the Anthropic API key ---
ENV_FILE="$BACKEND_DIR/.env"
if [ ! -f "$ENV_FILE" ] || ! grep -qi "anthropic_api_key" "$ENV_FILE"; then
  echo "Missing Anthropic API key."
  echo "Create backend/.env with:"
  echo "  ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

# --- Install frontend deps on first run ---
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
fi

# --- Start the backend (no --reload: the file watcher would kill renders) ---
echo "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT ..."
(
  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  exec uvicorn main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

# --- Stop the backend whenever this script exits (e.g. Ctrl+C) ---
cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# --- Start the frontend in the foreground ---
echo "Backend running at http://$BACKEND_HOST:$BACKEND_PORT"
echo "Starting frontend (Vite) at http://$BACKEND_HOST:5173 ..."
echo "Press Ctrl+C to stop both servers."
cd "$FRONTEND_DIR"
npm run dev
