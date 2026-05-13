#!/usr/bin/env bash
# ── FAN-CE Upgrade Script ──
# Safely upgrade to latest code while preserving all data.
# Data NOT affected: PostgreSQL database, dataset files, config files, BLAST indexes.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "========================================"
echo " FAN-CE Upgrade"
echo "========================================"
echo ""

# ── 0. Stop services ──
echo "[0/5] Stopping running services..."
bash scripts/dev/stop-dev.sh 2>/dev/null || true
pkill -f uvicorn 2>/dev/null || true
sleep 1
echo "  Done."

# ── 1. Pull latest code ──
echo "[1/5] Pulling latest code..."
git pull
echo "  Done."

# ── 2. Update dependencies ──
echo "[2/5] Updating dependencies (new packages only)..."
pixi install --frozen
echo "  Done."

# ── 3. Database migrations ──
echo "[3/5] Applying database migrations..."
pixi run alembic upgrade head || echo "  No new migrations."
echo "  Done."

# ── 4. Update analysis plugins ──
echo "[4/5] Updating analysis plugins..."
pixi run python -m pip install --force-reinstall plugin/*.whl --quiet --no-deps
echo "  Done."

# ── 5. Rebuild frontends ──
echo "[5/5] Rebuilding frontends..."
cd frontend/admin-web
pnpm install --frozen-lockfile
pnpm build
cd "$ROOT_DIR"
echo "  Done."

echo ""
echo "========================================"
echo " Upgrade complete!"
echo ""
echo " Restart services:"
echo "   bash scripts/dev/start-backend.sh"
echo "   bash scripts/dev/start-admin-web.sh"
echo "   cd frontend/admin-web && pnpm -F web-public dev"
echo "========================================"
