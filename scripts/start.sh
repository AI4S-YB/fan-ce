#!/usr/bin/env bash
# ── FAN-CE Service Startup ──
#   [1] Development — 127.0.0.1, hot reload, default ports
#   [2] Debug       — 0.0.0.0,   hot reload, default ports (remote debugging)
#   [3] Production  — 0.0.0.0,   no reload,  custom ports  (public deployment)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Default ports ──
BACKEND_PORT=8002
ADMIN_PORT=5666
PUBLIC_PORT=5677

# ── Detect pixi (not always in PATH when called via nohup) ──
PIXI_BIN=""
for candidate in "$HOME/.pixi/bin/pixi" "/usr/local/bin/pixi" "/opt/pixi/bin/pixi"; do
    [ -x "$candidate" ] && { PIXI_BIN="$candidate"; break; }
done
if [ -z "$PIXI_BIN" ]; then
    PIXI_BIN="$(command -v pixi 2>/dev/null)" || {
        echo -e "${RED}pixi not found. Install: https://pixi.sh${NC}"
        exit 1
    }
fi

# ── Helpers ──
_validate_port() {
    local port="$1"
    [[ "$port" =~ ^[0-9]+$ ]] && [ "$port" -ge 1 ] && [ "$port" -le 65535 ] && return 0
    echo -e "${RED}Invalid port: $port${NC}"
    return 1
}

_check_low_port() { [ "$1" -lt 1024 ]; }

_show_nginx_help() {
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  Port $1 (<1024) requires root or nginx${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Template: ${ROOT_DIR}/templates/nginx-fance.conf${NC}"
    echo ""
    echo "  Quick setup:"
    echo "    sudo cp templates/nginx-fance.conf /etc/nginx/sites-available/fan-ce"
    echo "    sudo nano /etc/nginx/sites-available/fan-ce  # edit domain/paths"
    echo "    sudo ln -s /etc/nginx/sites-available/fan-ce /etc/nginx/sites-enabled/"
    echo "    sudo nginx -t && sudo systemctl reload nginx"
    echo ""
    echo -e "  Then run FAN-CE on high ports (>1024) and let nginx proxy to them."
    echo ""
    echo "  Use port $1 anyway? [y/N]"
    read -r confirm
    [ "$confirm" = "y" ] || [ "$confirm" = "Y" ] || { echo "  Aborted."; exit 1; }
}

# ── Mode selection ──
echo "========================================"
echo " FAN-CE  —  Service Startup"
echo "========================================"
echo ""
echo "  Choose run mode:"
echo "    [1] Development — 127.0.0.1 , hot reload, default ports"
echo "        (localhost only, changes apply instantly)"
echo ""
echo "    [2] Debug       — 0.0.0.0   , hot reload, default ports"
echo "        (remote access enabled, changes apply instantly)"
echo ""
echo "    [3] Production  — 0.0.0.0   , no reload,  custom ports"
echo "        (public deployment, requires pre-built frontend)"
echo ""
read -rp "  Enter 1, 2, or 3 [1]: " mode
mode="${mode:-1}"

case "$mode" in
    1)
        HOST="127.0.0.1"
        RELOAD="--reload"
        USE_PREVIEW=false
        echo -e "  ${GREEN}Development mode${NC}"
        ;;
    2)
        HOST="0.0.0.0"
        RELOAD="--reload"
        USE_PREVIEW=false
        echo -e "  ${CYAN}Debug mode — hot reload on $HOST${NC}"
        ;;
    3)
        HOST="0.0.0.0"
        RELOAD=""
        USE_PREVIEW=true
        echo -e "  ${YELLOW}Production mode${NC}"
        echo ""
        echo "  Configure ports (press Enter for defaults):"
        read -rp "    Backend API   [$BACKEND_PORT]: " p
        BACKEND_PORT="${p:-$BACKEND_PORT}"
        read -rp "    Admin panel   [$ADMIN_PORT]: " p
        ADMIN_PORT="${p:-$ADMIN_PORT}"
        read -rp "    Public portal [$PUBLIC_PORT]: " p
        PUBLIC_PORT="${p:-$PUBLIC_PORT}"
        for port in "$BACKEND_PORT" "$ADMIN_PORT" "$PUBLIC_PORT"; do
            _validate_port "$port" || exit 1
        done
        for port in "$PUBLIC_PORT" "$ADMIN_PORT" "$BACKEND_PORT"; do
            _check_low_port "$port" && _show_nginx_help "$port" && break
        done

        # Production mode: check frontend dist exists
        if [ ! -f "$ROOT_DIR/frontend/admin-web/apps/web-antd/dist/index.html" ]; then
            echo ""
            echo -e "${RED}  Production mode requires pre-built frontend.${NC}"
            echo -e "  ${YELLOW}  Build it first:${NC}"
            echo "    cd frontend/admin-web"
            echo "    pnpm -F @fan-ce/admin-web-antd build"
            echo "    pnpm -F @fan-ce/web-public build"
            echo ""
            read -rp "  Build now? [Y/n] " build_now
            build_now="${build_now:-y}"
            if [ "$build_now" = "y" ] || [ "$build_now" = "Y" ]; then
                echo "  Building frontends..."
                cd "$ROOT_DIR/frontend/admin-web"
                pnpm -F @fan-ce/admin-web-antd build
                pnpm -F @fan-ce/web-public build
                cd "$ROOT_DIR"
            else
                exit 1
            fi
        fi
        ;;
    *)
        echo -e "${RED}Invalid choice.${NC}"
        exit 1
        ;;
esac

echo ""
echo "──────────────────────────────────────────"
echo "  Backend API:    http://$HOST:$BACKEND_PORT"
echo "  Admin panel:    http://$HOST:$ADMIN_PORT"
echo "  Public portal:  http://$HOST:$PUBLIC_PORT"
if [ "$RELOAD" = "--reload" ]; then
    echo "  Mode:           hot reload enabled"
else
    echo "  Mode:           production (static serve)"
fi
echo "──────────────────────────────────────────"
echo ""

# ── Stop existing services ──
echo "Stopping existing services..."
bash "$ROOT_DIR/scripts/stop.sh" 2>/dev/null || true

# ── Start backend ──
echo ""
echo "Starting backend API (port $BACKEND_PORT)..."
cd "$ROOT_DIR"
nohup "$PIXI_BIN" run uv run --directory backend uvicorn main:app \
    --host "$HOST" --port "$BACKEND_PORT" $RELOAD \
    > /tmp/fance-backend.log 2>&1 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# ── Start admin frontend ──
echo "Starting admin panel (port $ADMIN_PORT)..."
cd "$ROOT_DIR/frontend/admin-web"
if [ "$USE_PREVIEW" = true ]; then
    nohup pnpm -F @fan-ce/admin-web-antd exec vite preview --host "$HOST" --port "$ADMIN_PORT" \
        > /tmp/fance-admin.log 2>&1 &
else
    nohup pnpm -F @fan-ce/admin-web-antd run dev -- --host "$HOST" --port "$ADMIN_PORT" \
        > /tmp/fance-admin.log 2>&1 &
fi
ADMIN_PID=$!
echo "  Admin PID: $ADMIN_PID"

# ── Start public portal ──
echo "Starting public portal (port $PUBLIC_PORT)..."
cd "$ROOT_DIR/frontend/admin-web"
nohup pnpm -F @fan-ce/web-public exec vite --host "$HOST" --port "$PUBLIC_PORT" \
    > /tmp/fance-public.log 2>&1 &
PUBLIC_PID=$!
echo "  Public PID: $PUBLIC_PID"

# Save PID info for stop.sh
cat > /tmp/fance-services.env <<EOF
BACKEND_PID=$BACKEND_PID
ADMIN_PID=$ADMIN_PID
PUBLIC_PID=$PUBLIC_PID
BACKEND_PORT=$BACKEND_PORT
ADMIN_PORT=$ADMIN_PORT
PUBLIC_PORT=$PUBLIC_PORT
EOF

echo ""
echo -e "${GREEN}All services started.${NC}"
echo ""
echo "  Logs:"
echo "    Backend:  tail -f /tmp/fance-backend.log"
echo "    Admin:    tail -f /tmp/fance-admin.log"
echo "    Public:   tail -f /tmp/fance-public.log"
echo ""
echo "  Stop all:  bash scripts/stop.sh"
