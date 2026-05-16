#!/usr/bin/env bash
# ── FAN-CE Service Startup ──
# Supports development (localhost) and production (public-facing) modes.
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

# ── Helpers ──
_validate_port() {
    local port="$1"
    if [[ ! "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
        echo -e "${RED}Invalid port: $port${NC}"
        return 1
    fi
    return 0
}

_check_low_port() {
    local port="$1"
    if [ "$port" -lt 1024 ]; then
        return 0  # is a low port
    fi
    return 1  # is a high port
}

_show_nginx_help() {
    local public_port="$1"
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  Port $public_port (<1024) requires root or nginx${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${CYAN}Recommended: nginx reverse proxy${NC}"
    echo -e "  Template: ${CYAN}$ROOT_DIR/templates/nginx-fance.conf${NC}"
    echo ""
    echo -e "  ${GREEN}Quick setup:${NC}"
    echo "    # 1. Copy & edit the template"
    echo "    sudo cp templates/nginx-fance.conf /etc/nginx/sites-available/fan-ce"
    echo "    sudo nano /etc/nginx/sites-available/fan-ce  # change domain/paths"
    echo ""
    echo "    # 2. Enable the site"
    echo "    sudo ln -s /etc/nginx/sites-available/fan-ce /etc/nginx/sites-enabled/"
    echo "    sudo nginx -t && sudo systemctl reload nginx"
    echo ""
    echo "    # 3. Start FAN-CE on high ports instead:"
    echo -e "    ${CYAN}bash scripts/start.sh${NC}  → choose production → use ports >1024"
    echo ""
    echo "  Then nginx handles port 80, forwarding to FAN-CE internally."
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Continue with port $public_port anyway? [y/N]"
    read -r confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "  Aborted."
        exit 1
    fi
}

# ── Mode selection ──
echo "========================================"
echo " FAN-CE Service Startup"
echo "========================================"
echo ""
echo " Choose run mode:"
echo "   [1] Development  — 127.0.0.1, hot reload, default ports"
echo "   [2] Production   — 0.0.0.0, no reload, customizable ports"
echo "   [3] Custom       — configure host and ports per service"
echo ""
read -rp " Enter 1, 2, or 3 [1]: " mode
mode="${mode:-1}"

case "$mode" in
    1)
        HOST="127.0.0.1"
        RELOAD="--reload"
        echo -e "  ${GREEN}Development mode — http://$HOST${NC}"
        ;;
    2)
        HOST="0.0.0.0"
        RELOAD=""
        echo -e "  ${YELLOW}Production mode — binding to $HOST${NC}"
        echo ""
        echo "  Configure ports (press Enter for defaults):"
        read -rp "    Backend API [$BACKEND_PORT]: " p
        BACKEND_PORT="${p:-$BACKEND_PORT}"
        read -rp "    Admin panel [$ADMIN_PORT]: " p
        ADMIN_PORT="${p:-$ADMIN_PORT}"
        read -rp "    Public portal [$PUBLIC_PORT]: " p
        PUBLIC_PORT="${p:-$PUBLIC_PORT}"

        # Validate
        for port in "$BACKEND_PORT" "$ADMIN_PORT" "$PUBLIC_PORT"; do
            _validate_port "$port" || exit 1
        done

        # Check low ports
        for port in "$PUBLIC_PORT" "$ADMIN_PORT" "$BACKEND_PORT"; do
            if _check_low_port "$port"; then
                _show_nginx_help "$port"
                break
            fi
        done
        ;;
    3)
        echo ""
        echo "  Configure each service:"
        read -rp "    Bind host [0.0.0.0]: " HOST
        HOST="${HOST:-0.0.0.0}"
        read -rp "    Hot reload? [y/N]: " r
        if [ "$r" = "y" ] || [ "$r" = "Y" ]; then RELOAD="--reload"; else RELOAD=""; fi
        read -rp "    Backend API port [$BACKEND_PORT]: " p
        BACKEND_PORT="${p:-$BACKEND_PORT}"
        read -rp "    Admin panel port [$ADMIN_PORT]: " p
        ADMIN_PORT="${p:-$ADMIN_PORT}"
        read -rp "    Public portal port [$PUBLIC_PORT]: " p
        PUBLIC_PORT="${p:-$PUBLIC_PORT}"
        for port in "$BACKEND_PORT" "$ADMIN_PORT" "$PUBLIC_PORT"; do
            _validate_port "$port" || exit 1
        done
        for port in "$PUBLIC_PORT" "$ADMIN_PORT" "$BACKEND_PORT"; do
            if _check_low_port "$port"; then
                _show_nginx_help "$port"
                break
            fi
        done
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
echo "──────────────────────────────────────────"
echo ""

# ── Stop existing services ──
echo "Stopping existing services..."
bash "$ROOT_DIR/scripts/dev/stop-dev.sh" 2>/dev/null || true

# ── Start backend ──
echo ""
echo "Starting backend API (port $BACKEND_PORT)..."
cd "$ROOT_DIR"
nohup pixi run uv run --directory backend/api-server uvicorn main:app \
    --host "$HOST" --port "$BACKEND_PORT" $RELOAD \
    > /tmp/fance-backend.log 2>&1 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# ── Start admin frontend ──
echo "Starting admin panel (port $ADMIN_PORT)..."
cd "$ROOT_DIR/frontend/admin-web"
if [ "$RELOAD" = "--reload" ]; then
    nohup pnpm -F @fan-ce/admin-web-antd run dev -- --host "$HOST" --port "$ADMIN_PORT" \
        > /tmp/fance-admin.log 2>&1 &
else
    # Production: use vite preview (serve built dist)
    nohup pnpm -F @fan-ce/admin-web-antd exec vite preview --host "$HOST" --port "$ADMIN_PORT" \
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

echo ""
echo -e "${GREEN}All services started.${NC}"
echo ""
echo "  Logs:"
echo "    Backend:  tail -f /tmp/fance-backend.log"
echo "    Admin:    tail -f /tmp/fance-admin.log"
echo "    Public:   tail -f /tmp/fance-public.log"
echo ""
echo "  Stop all:  bash scripts/dev/stop-dev.sh"
