#!/usr/bin/env bash
# ── FAN-CE Install Script ──
# Fresh installation from source.
# Prerequisites: pixi (https://pixi.sh), pnpm, Node.js >= 20, PostgreSQL
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "========================================"
echo " FAN-CE Installation"
echo "========================================"
echo ""

# ── 1. System dependencies via pixi ──
echo "[1/5] Installing bioinformatics tools + Python packages via pixi..."
pixi install
echo "  Done."

# ── 2. Analysis plugins ──
echo "[2/5] Installing analysis plugins..."
pixi run python -m pip install plugin/*.whl --quiet --no-deps
echo "  Done."

# ── 3. Database migration ──
echo "[3/5] Running database migrations..."
if [ -f "conf/config.dev.yaml" ] || [ -f "conf/config.prod.yaml" ]; then
    pixi run alembic upgrade head || echo "  Warning: alembic not configured. Skipping migrations."
else
    echo "  Warning: No configuration file found. Create conf/config.dev.yaml first."
    echo "  See conf/config.example.yaml for reference."
fi
echo "  Done."

# ── 4. Frontend ──
echo "[4/5] Building frontends..."
cd frontend/admin-web
pnpm install --frozen-lockfile
pnpm build
cd "$ROOT_DIR"
echo "  Done."

# ── 5. Verify ──
echo "[5/5] Verifying installation..."
echo ""
echo "  Tools:"
for tool in samtools bcftools blastn primer3_core mafft FastTree; do
    if pixi run which "$tool" &>/dev/null; then
        echo "    $tool  ✓"
    else
        echo "    $tool  ✗ (not found)"
    fi
done
echo ""
echo "========================================"
echo " Installation complete!"
echo ""
echo " Start the application:"
echo "   bash scripts/dev/start-backend.sh"
echo "   bash scripts/dev/start-admin-web.sh"
echo "   cd frontend/admin-web && pnpm -F web-public dev"
echo ""
echo " Server ports:"
echo "   Backend API:     http://localhost:8002"
echo "   Admin (antd):    http://localhost:5666"
echo "   Public portal:   http://localhost:5677"
echo "========================================"
