#!/usr/bin/env bash
# ── FAN-CE Upgrade Script ──
# Safely upgrade to latest code while preserving all data.
# Supports macOS and Linux.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONF_FILE="backend/api-server/conf/config.dev.yaml"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo " FAN-CE Upgrade"
echo "========================================"
echo ""

# ── 0. Stop services ──
echo "[0/6] Stopping running services..."
bash scripts/dev/stop-dev.sh 2>/dev/null || true
pkill -f uvicorn 2>/dev/null || true
sleep 1
echo "  Done."

# Ensure PostgreSQL container is running
PG_CONTAINER="fance-postgres"
if ! docker exec "$PG_CONTAINER" pg_isready -q 2>/dev/null; then
    echo -e "  ${YELLOW}PostgreSQL container ($PG_CONTAINER) is not running.${NC}"
    echo -e "  ${YELLOW}Please start it: docker start $PG_CONTAINER${NC}"
    exit 1
fi

# ── 1. Pull latest code ──
echo "[1/6] Pulling latest code..."
git pull
echo "  Done."

# ── 2. Update dependencies ──
echo "[2/6] Updating dependencies..."
pixi install --frozen
pixi run uv sync --directory backend/api-server
echo "  Done."

# ── 3. Database migrations ──
echo "[3/6] Applying database migrations..."
pixi run uv run --directory backend/api-server alembic upgrade head || \
    echo -e "  ${YELLOW}Warning: alembic upgrade had errors (may be harmless).${NC}"
echo "  Done."

# ── 4. Check / import taxonomy ──
echo "[4/6] Checking plant taxonomy data..."
TAXONOMY_DATA="$ROOT_DIR/backend/api-server/data/taxonomy-plants.tar.gz"
if [ -f "$TAXONOMY_DATA" ]; then
    pixi run uv run --directory backend/api-server python -c "
from db.database import MyDBManager
from apps.breeding.models import BreedingTaxonomyNode
with MyDBManager() as db:
    count = db.query(BreedingTaxonomyNode).count()
    if count > 0:
        print(f'  Taxonomy installed ({count:,} nodes).')
        print('  To update, use admin panel: Platform Setup → Update Taxonomy')
    else:
        print('  No taxonomy data found. Run scripts/init_taxonomy.py to import.')
" || true
else
    echo -e "  ${YELLOW}Taxonomy data file not found. Skipping.${NC}"
fi
echo ""

# ── 5. Update analysis plugins ──
echo "[5/6] Updating analysis plugins..."
if ls plugin/*.whl &>/dev/null 2>&1; then
    pixi run uv run --directory backend/api-server pip install --force-reinstall plugin/*.whl --no-deps
fi
echo "  Done."

# ── 6. Rebuild frontends ──
echo "[6/6] Rebuilding frontends..."
cd frontend/admin-web
pnpm install --frozen-lockfile
pnpm -F @fan-ce/admin-web-antd -F @fan-ce/web-public build
cd "$ROOT_DIR"
echo "  Done."

echo ""
echo "========================================"
echo -e " ${GREEN}Upgrade complete!${NC}"
echo ""
echo " Restart services:"
echo "   bash scripts/start.sh"
echo "========================================"
