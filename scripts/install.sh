#!/usr/bin/env bash
# ── FAN-CE Install Script ──
# Fresh installation from source.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONF_DIR="backend/api-server/conf"
CONF_FILE="${CONF_DIR}/config.dev.yaml"
CONF_EXAMPLE="${CONF_DIR}/config.example.yaml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo " FAN-CE Installation"
echo "========================================"
echo ""

# ── 0. Prerequisites ──
echo "[0/5] Checking prerequisites..."
MISSING=""

command -v pixi &>/dev/null || MISSING="$MISSING  pixi (https://pixi.sh)\n"
command -v pnpm &>/dev/null || MISSING="$MISSING  pnpm (https://pnpm.io)\n"
command -v psql &>/dev/null || command -v pg_isready &>/dev/null || MISSING="$MISSING  PostgreSQL client\n"

if command -v node &>/dev/null; then
    NODE_VER=$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VER" -lt 20 ] 2>/dev/null; then
        MISSING="$MISSING  Node.js >= 20 (found $(node -v))\n"
    fi
fi

if [ -n "$MISSING" ]; then
    echo -e "${RED}Missing prerequisites:${NC}"
    echo -e "$MISSING"
    exit 1
fi
echo -e "  ${GREEN}All prerequisites met.${NC}"

# Check config file exists
if [ ! -f "$CONF_FILE" ]; then
    if [ -f "$CONF_EXAMPLE" ]; then
        echo -e "  ${YELLOW}No config.dev.yaml found. Copying from example...${NC}"
        cp "$CONF_EXAMPLE" "$CONF_FILE"
        echo "  Copied $CONF_EXAMPLE -> $CONF_FILE"
        echo -e "  ${YELLOW}IMPORTANT: Edit $CONF_FILE with your database credentials.${NC}"
    else
        echo -e "${RED}No configuration file found at $CONF_FILE${NC}"
        exit 1
    fi
fi
echo ""

# ── 1. Pixi + Python environment ──
echo "[1/5] Installing bioinformatics tools + Python environment..."
pixi install
pixi run uv sync --directory backend/api-server
echo -e "  ${GREEN}Done.${NC}"
echo ""

# ── 2. Data directories ──
echo "[2/5] Creating data directories..."
mkdir -p /data/biodata 2>/dev/null || echo -e "  ${YELLOW}Warning: Could not create /data/biodata. Create it manually or update the path in config.${NC}"
echo -e "  ${GREEN}Done.${NC}"
echo ""

# ── 3. Database migration ──
echo "[3/5] Running database migrations..."
pixi run uv run --directory backend/api-server alembic upgrade head || echo -e "  ${YELLOW}Warning: alembic upgrade failed. Check database connection in $CONF_FILE${NC}"
echo -e "  ${GREEN}Done.${NC}"
echo ""

# ── 4. Frontend ──
echo "[4/5] Building frontends..."
cd frontend/admin-web
pnpm install --frozen-lockfile
pnpm build
cd "$ROOT_DIR"
echo -e "  ${GREEN}Done.${NC}"
echo ""

# ── 5. Verify ──
echo "[5/5] Verifying installation..."
echo ""
echo "  Bio-tools:"
for tool in samtools bcftools blastn primer3_core mafft FastTree; do
    if pixi run which "$tool" &>/dev/null; then
        echo -e "    $tool  ${GREEN}✓${NC}"
    else
        echo -e "    $tool  ${RED}✗${NC}"
    fi
done
echo ""
echo "========================================"
echo -e " ${GREEN}Installation complete!${NC}"
echo ""
echo " Start the application:"
echo "   bash scripts/dev/start-backend.sh"
echo "   bash scripts/dev/start-admin-web.sh"
echo "   cd frontend/admin-web && pnpm -F web-public dev"
echo ""
echo " Log in at http://localhost:5666"
echo "   Username: admin"
echo "   Password: Admin123456"
echo "========================================"
