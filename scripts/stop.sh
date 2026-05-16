#!/usr/bin/env bash
# ── FAN-CE Service Stop ──
# Stop all running FAN-CE services (dev or production mode).
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

STOPPED=0

_kill_port() {
    local port="$1" label="$2"
    local pid
    pid=$(lsof -ti:"$port" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        kill -9 $pid 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} $label (port $port)"
        STOPPED=$((STOPPED + 1))
    fi
}

_kill_process() {
    local pattern="$1" label="$2"
    local pids
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} $label"
        STOPPED=$((STOPPED + 1))
    fi
}

echo "========================================"
echo " FAN-CE — Stopping Services"
echo "========================================"

# ── 1. Try PID file from start.sh ──
if [ -f /tmp/fance-services.env ]; then
    # shellcheck disable=SC1091
    source /tmp/fance-services.env
    for var in BACKEND_PID ADMIN_PID PUBLIC_PID; do
        pid="${!var:-}"
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null || true
            echo -e "  ${GREEN}✓${NC} $var (PID $pid)"
            STOPPED=$((STOPPED + 1))
        fi
    done
    # Also kill child processes spawned by these
    for pid in "${BACKEND_PID:-}" "${ADMIN_PID:-}" "${PUBLIC_PID:-}"; do
        [ -n "$pid" ] && pkill -P "$pid" 2>/dev/null || true
    done
    rm -f /tmp/fance-services.env
fi

# ── 2. Port-based cleanup (handles custom ports) ──
for port in 8002 5666 5677; do
    _kill_port "$port" "Service on port $port"
done

# ── 3. Process-based cleanup (catches anything left) ──
_kill_process "uvicorn main:app"    "Backend (uvicorn)"
_kill_process "vite.*--port"         "Frontend (vite)"
_kill_process "pnpm.*dev:antd\|pnpm.*dev web-public" "Frontend (pnpm dev)"
_kill_process "pixi run backend"    "Backend (pixi)"

# ── 4. Clean up log files ──
rm -f /tmp/fance-backend.log /tmp/fance-admin.log /tmp/fance-public.log

echo ""
if [ "$STOPPED" -eq 0 ]; then
    echo "No running FAN-CE services found."
else
    echo -e "${GREEN}All FAN-CE services stopped.${NC}"
fi
