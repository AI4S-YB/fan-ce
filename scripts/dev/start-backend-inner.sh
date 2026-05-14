#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend/api-server"
PIXI_ENV_BIN="$ROOT_DIR/.pixi/envs/default/bin"

# Add pixi bio-tools to PATH (samtools, blast, etc.)
if [ -d "$PIXI_ENV_BIN" ]; then
  export PATH="$PIXI_ENV_BIN:$PATH"
fi

# Use .venv Python for the backend itself
if [ -x "$BACKEND_DIR/.venv/bin/uvicorn" ]; then
  UVICORN_BIN="$BACKEND_DIR/.venv/bin/uvicorn"
  PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
elif [ -x "$ROOT_DIR/.venv/bin/uvicorn" ]; then
  UVICORN_BIN="$ROOT_DIR/.venv/bin/uvicorn"
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  echo "uvicorn not found in $BACKEND_DIR/.venv or $ROOT_DIR/.venv" >&2
  echo "Set up a Python virtual environment first." >&2
  exit 1
fi

cd "$BACKEND_DIR"

if [ -z "${APP_ENV:-}" ] || [ "${APP_ENV:-}" = "dev" ]; then
  if ! APP_ENV=dev "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import psycopg
from core.config import settings

pgsql_options = settings.app_options.get("pgsql_options") or {}
conn = psycopg.connect(
    host=pgsql_options.get("host", "127.0.0.1"),
    port=pgsql_options.get("port", 5432),
    dbname=pgsql_options.get("database", "fan_ce_dev"),
    user=pgsql_options.get("user", "postgres"),
    password=pgsql_options.get("password", ""),
    connect_timeout=int(pgsql_options.get("connect_timeout", 3) or 3),
)
conn.close()
PY
  then
    export APP_ENV=dev-sqlite
    echo "PostgreSQL unavailable, fallback to APP_ENV=$APP_ENV" >&2
  fi
fi

APP_ENV="${APP_ENV:-dev}" "$UVICORN_BIN" main:app \
  --host 127.0.0.1 \
  --port 8002 \
  --reload \
  --reload-dir apps \
  --reload-dir basis \
  --reload-dir core \
  --reload-dir db \
  --reload-dir libs \
  --reload-dir register \
  --reload-dir conf \
  --reload-dir utils \
  --reload-dir static
