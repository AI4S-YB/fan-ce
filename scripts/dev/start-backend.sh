#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if command -v pixi >/dev/null 2>&1 && [ -f "$ROOT_DIR/pixi.toml" ]; then
  exec pixi run --manifest-path "$ROOT_DIR" backend-dev
fi

exec "$ROOT_DIR/scripts/dev/start-backend-inner.sh"
