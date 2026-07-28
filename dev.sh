#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
BACKEND_PYTHON_VERSION="${BACKEND_PYTHON_VERSION:-3.11}"

if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

port_is_free() {
  local host="$1"
  local port="$2"
  python3 -c "import socket, sys
host = sys.argv[1]
port = int(sys.argv[2])
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        result = sock.connect_ex((host, port))
except OSError as exc:
    print(f\"Unable to check {host}:{port}: {exc}\", file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(0 if result != 0 else 1)
" "$host" "$port"
}

find_free_port() {
  local host="$1"
  local port="$2"
  local status
  while true; do
    if port_is_free "$host" "$port"; then
      printf '%s' "$port"
      return
    else
      status=$?
    fi
    if [ "$status" -ne 1 ]; then
      return "$status"
    fi
    port=$((port + 1))
  done
}

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
BACKEND_PORT="$(find_free_port "$BACKEND_HOST" "${BACKEND_PORT:-8010}")"
FRONTEND_PORT="$(find_free_port "$FRONTEND_HOST" "${FRONTEND_PORT:-5174}")"

current_python_version=""
if [ -x "$VENV_DIR/bin/python" ]; then
  current_python_version="$("$VENV_DIR/bin/python" -c \
    'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' \
    2>/dev/null || true)"
fi

if [ "$current_python_version" != "$BACKEND_PYTHON_VERSION" ]; then
  if [ -n "$current_python_version" ]; then
    echo "Recreating backend virtual environment: Python $current_python_version -> $BACKEND_PYTHON_VERSION"
  fi

  if command -v uv >/dev/null 2>&1; then
    uv venv --clear --seed --python "$BACKEND_PYTHON_VERSION" "$VENV_DIR"
  else
    backend_python_bin="${BACKEND_PYTHON_BIN:-python$BACKEND_PYTHON_VERSION}"
    if ! command -v "$backend_python_bin" >/dev/null 2>&1; then
      echo "Python $BACKEND_PYTHON_VERSION is required. Install it or uv, or set BACKEND_PYTHON_BIN." >&2
      exit 1
    fi
    "$backend_python_bin" -m venv --clear "$VENV_DIR"
  fi
fi

"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  npm --prefix "$FRONTEND_DIR" install
fi

"$VENV_DIR/bin/python" "$BACKEND_DIR/manage.py" migrate
"$VENV_DIR/bin/python" "$BACKEND_DIR/manage.py" seed_solaris

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

"$VENV_DIR/bin/python" "$BACKEND_DIR/manage.py" runserver "$BACKEND_HOST:$BACKEND_PORT" &
VITE_HOST="$FRONTEND_HOST" \
VITE_PORT="$FRONTEND_PORT" \
VITE_BACKEND_TARGET="http://$BACKEND_HOST:$BACKEND_PORT" \
  npm --prefix "$FRONTEND_DIR" run dev
