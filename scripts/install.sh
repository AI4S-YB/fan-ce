#!/usr/bin/env bash
# ── FAN-CE Install Script ──
# Fresh installation from source.
# Supports macOS and Linux (x86_64 / arm64).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONF_DIR="backend/api-server/conf"
CONF_FILE="${CONF_DIR}/config.dev.yaml"
CONF_EXAMPLE="${CONF_DIR}/config.example.yaml"
TAXONOMY_DATA="$ROOT_DIR/backend/api-server/data/taxonomy-plants.tar.gz"
INIT_SCRIPT="$ROOT_DIR/scripts/init_taxonomy.py"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo " FAN-CE Installation"
echo "========================================"
echo ""

# ── 0. Prerequisites ──
echo "[0/6] Checking prerequisites..."
MISSING=""

command -v pixi &>/dev/null || MISSING="$MISSING  pixi (https://pixi.sh)\n"
command -v pnpm &>/dev/null || MISSING="$MISSING  pnpm (https://pnpm.io)\n"

# PostgreSQL client check (need either psql or pg_isready)
command -v psql &>/dev/null || command -v pg_isready &>/dev/null || {
    # On Linux, try common install paths
    if [ -f /usr/bin/psql ] || [ -f /usr/local/bin/psql ]; then
        :
    else
        MISSING="$MISSING  PostgreSQL client (psql or pg_isready)\n"
    fi
}

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
echo "[1/6] Installing bioinformatics tools + Python environment..."
pixi install
pixi run uv sync --directory backend/api-server
echo -e "  ${GREEN}Done.${NC}"
echo ""

# ── 2. Data directories ──
echo "[2/6] Checking data directory..."
echo -e "  ${YELLOW}Configure apps.databases.fileDir in $CONF_FILE to point to your data storage location.${NC}"
echo -e "  ${GREEN}Done.${NC}"
echo ""

# ── 3. PostgreSQL + Database setup ──
echo "[3/6] Setting up PostgreSQL..."

# Read DB config from yaml under pgsql_options section
_parse_pgsql_opt() {
    awk "/^pgsql_options:/{found=1; next} found && /^[a-z]/{exit} found && /  $1:/{gsub(/.*:\s*/,\"\"); print; exit}" "$CONF_FILE" | xargs
}
DB_HOST=$(_parse_pgsql_opt host)
DB_PORT=$(_parse_pgsql_opt port)
DB_NAME=$(_parse_pgsql_opt database)
DB_USER=$(_parse_pgsql_opt user)
DB_PASS=$(_parse_pgsql_opt password)

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5433}"
DB_NAME="${DB_NAME:-fan_ce_dev}"
DB_USER="${DB_USER:-fan_api}"
DB_PASS="${DB_PASS:-fan_api_dev}"

if command -v pg_isready &>/dev/null; then
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -q 2>/dev/null; then
        echo -e "  ${GREEN}PostgreSQL is running at $DB_HOST:$DB_PORT${NC}"
    else
        echo -e "  ${YELLOW}PostgreSQL not reachable. Attempting to start via Docker...${NC}"
        if command -v docker &>/dev/null; then
            # Remove stale container if exists
            docker rm -f fance-postgres 2>/dev/null || true
            # Try docker compose then docker-compose (Linux compat)
            if docker compose version &>/dev/null 2>&1; then
                docker compose -f docker-compose.yml up -d postgres 2>/dev/null || true
            elif command -v docker-compose &>/dev/null; then
                docker-compose -f docker-compose.yml up -d postgres 2>/dev/null || true
            fi
            # Fallback: run postgres directly
            if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -q 2>/dev/null; then
                echo -e "  ${YELLOW}Starting PostgreSQL container...${NC}"
                docker run -d --name fance-postgres \
                    -p "$DB_PORT:5432" \
                    -e "POSTGRES_USER=$DB_USER" \
                    -e "POSTGRES_PASSWORD=$DB_PASS" \
                    -e "POSTGRES_DB=$DB_NAME" \
                    postgres:16 2>/dev/null || echo -e "  ${YELLOW}Could not start PostgreSQL. Please start it manually.${NC}"
            fi
            sleep 3
        else
            echo -e "  ${YELLOW}Docker not found. Please start PostgreSQL manually.${NC}"
        fi
    fi
fi

# Create database if it doesn't exist
if command -v psql &>/dev/null && pg_isready -h "$DB_HOST" -p "$DB_PORT" -q 2>/dev/null; then
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tc \
        "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" 2>/dev/null | grep -q 1 || {
        echo -e "  ${YELLOW}Database '$DB_NAME' not found. Creating...${NC}"
        PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c \
            "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true
    }
fi

# Skip alembic for fresh installs (tables created by init_*_tables functions).
# Only run migrations if tables already exist (upgrade scenario).
TABLE_COUNT=$(PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tc \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | xargs || echo "0")
if [ "${TABLE_COUNT:-0}" -gt 10 ]; then
    echo "  Detected existing database ($TABLE_COUNT tables). Running migrations..."
    pixi run uv run --directory backend/api-server alembic upgrade head || \
        echo -e "  ${YELLOW}Warning: alembic upgrade had errors (may be harmless).${NC}"
else
    echo "  Fresh database detected. Tables will be created in next step."
fi
echo -e "  ${GREEN}Done.${NC}"
echo ""

# ── 4. Create tables + Import taxonomy ──
echo "[4/6] Initializing database tables and plant taxonomy..."
if [ -f "$TAXONOMY_DATA" ]; then
    pixi run uv run --directory backend/api-server python "$INIT_SCRIPT" "$TAXONOMY_DATA"
    echo -e "  ${GREEN}Done.${NC}"
else
    echo -e "  ${RED}Error: Taxonomy data file not found at $TAXONOMY_DATA${NC}"
    echo -e "  ${YELLOW}Run: python scripts/build/filter_plants.py <ncbi_dump> backend/api-server/data/${NC}"
    echo -e "  ${YELLOW}Then re-run this install script.${NC}"
    exit 1
fi
echo ""

# ── 5. Frontend ──
echo "[5/6] Building frontends..."
cd frontend/admin-web
pnpm install --frozen-lockfile
pnpm build
cd "$ROOT_DIR"
echo -e "  ${GREEN}Done.${NC}"
echo ""

# ── 6. Verify ──
echo "[6/6] Verifying installation..."
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
echo ""
echo " Plant taxonomy data is pre-loaded and ready."
echo " To update taxonomy data, use the admin panel:"
echo "   Platform Setup → Update Taxonomy"
echo "========================================"
