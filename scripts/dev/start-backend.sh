#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

# Auto-initialize uv venv on first run
if [ ! -d "backend/api-server/.venv" ]; then
  echo "Creating Python venv with uv..."
  uv venv backend/api-server/.venv --python 3.12
  uv sync --directory backend/api-server
fi

exec pixi run backend
