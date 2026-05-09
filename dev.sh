#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  python3 -m venv "$BACKEND_DIR/.venv"
fi

"$BACKEND_DIR/.venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  npm --prefix "$FRONTEND_DIR" install
fi

"$BACKEND_DIR/.venv/bin/python" "$BACKEND_DIR/manage.py" migrate
"$BACKEND_DIR/.venv/bin/python" "$BACKEND_DIR/manage.py" seed_solaris

cleanup() {
  jobs -p | xargs -r kill
}
trap cleanup EXIT

"$BACKEND_DIR/.venv/bin/python" "$BACKEND_DIR/manage.py" runserver 127.0.0.1:8000 &
npm --prefix "$FRONTEND_DIR" run dev
