#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

port_is_free() {
  local host="$1"
  local port="$2"
  python3 -c "import socket, sys
host = sys.argv[1]
port = int(sys.argv[2])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    raise SystemExit(0 if sock.connect_ex((host, port)) != 0 else 1)
" "$host" "$port"
}

find_free_port() {
  local host="$1"
  local port="$2"
  while ! port_is_free "$host" "$port"; do
    port=$((port + 1))
  done
  printf '%s' "$port"
}

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
BACKEND_PORT="$(find_free_port "$BACKEND_HOST" "${BACKEND_PORT:-8010}")"
FRONTEND_PORT="$(find_free_port "$FRONTEND_HOST" "${FRONTEND_PORT:-5174}")"

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
  local pids
  pids="$(jobs -pr)"
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
  fi
}
trap cleanup EXIT

export LOCAL_FRONTEND_HOST="$FRONTEND_HOST"
export LOCAL_FRONTEND_PORT="$FRONTEND_PORT"

echo "Backend:  http://$BACKEND_HOST:$BACKEND_PORT"
echo "Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"

"$BACKEND_DIR/.venv/bin/python" "$BACKEND_DIR/manage.py" runserver "$BACKEND_HOST:$BACKEND_PORT" &
VITE_HOST="$FRONTEND_HOST" \
VITE_PORT="$FRONTEND_PORT" \
VITE_BACKEND_TARGET="http://$BACKEND_HOST:$BACKEND_PORT" \
  npm --prefix "$FRONTEND_DIR" run dev
