#!/usr/bin/env bash
# ── FAN-CE Upgrade Script ──
# Safely upgrade to latest code while preserving all data.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
echo "[2/5] Updating dependencies..."
pixi install --frozen
pixi run uv sync --directory backend/api-server
echo "  Done."

# ── 3. Database migrations ──
echo "[3/5] Applying database migrations..."
pixi run uv run --directory backend/api-server alembic upgrade head || echo -e "  ${YELLOW}Warning: alembic upgrade failed.${NC}"
echo "  Done."

# ── 4. Update analysis plugins ──
echo "[4/5] Updating analysis plugins..."
if ls plugin/*.whl &>/dev/null 2>&1; then
    pixi run uv run --directory backend/api-server pip install --force-reinstall plugin/*.whl --no-deps
fi
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
echo -e " ${GREEN}Upgrade complete!${NC}"
echo ""
echo " Restart services:"
echo "   bash scripts/dev/start-backend.sh"
echo "   bash scripts/dev/start-admin-web.sh"
echo "   cd frontend/admin-web && pnpm -F web-public dev"
echo "========================================"
