#!/usr/bin/env bash
# ── FAN-CE Service Stop ──
# Stop all running FAN-CE services (dev / production / custom ports).
# Identifies services by PID file → port ownership → process cmdline match.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

STOPPED=0

# ── Helpers ──

# Check if a PID belongs to THIS FAN-CE installation.
# Uses the project root path as identifier — any process whose command
# line contains the project root path is considered ours.
_is_fance_pid() {
    local pid="$1"
    if [ ! -e "/proc/$pid" ]; then
        # macOS / BSD: check cmdline AND cwd
        # cmdline may use relative paths; cwd is the real anchor
        local cmdline cwd
        cmdline=$(ps -p "$pid" -o args= 2>/dev/null || true)
        [[ "$cmdline" == *"$ROOT_DIR"* ]] && return 0
        cwd=$(lsof -p "$pid" -a -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' || true)
        [[ "$cwd" == "$ROOT_DIR"* ]] && return 0
        # Check parent process recursively
        local ppid
        ppid=$(ps -p "$pid" -o ppid= 2>/dev/null | xargs || true)
        [ -n "$ppid" ] && _is_fance_pid "$ppid" && return 0
        return 1
    fi
    # Linux: check cmdline, cwd, and parent
    local cmdline cwd ppid
    cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
    [[ "$cmdline" == *"$ROOT_DIR"* ]] && return 0
    cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null || true)
    [[ "$cwd" == "$ROOT_DIR"* ]] && return 0
    ppid=$(awk '{print $4}' "/proc/$pid/stat" 2>/dev/null || true)
    [ -n "$ppid" ] && _is_fance_pid "$ppid" && return 0
    return 1
}

_kill_pid_tree() {
    local pid="$1" label="$2"
    if ! kill -0 "$pid" 2>/dev/null; then
        return 1
    fi
    echo -e "  ${GREEN}✓${NC} $label (PID $pid)"
    # Kill children first, then parent
    pkill -P "$pid" 2>/dev/null || true
    kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
    STOPPED=$((STOPPED + 1))
    return 0
}

echo "========================================"
echo " FAN-CE — Stopping Services"
echo "========================================"

# ── Layer 1: PID file from start.sh (100% precise) ──
if [ -f /tmp/fance-services.env ]; then
    echo "  [Layer 1] PID file"
    # shellcheck disable=SC1091
    source /tmp/fance-services.env
    for var in BACKEND_PID ADMIN_PID PUBLIC_PID; do
        pid="${!var:-}"
        if [ -n "$pid" ]; then
            _kill_pid_tree "$pid" "$var" || true
        fi
    done
    rm -f /tmp/fance-services.env
fi

# ── Layer 2: Port-based with PID verification ──
echo "  [Layer 2] Port scan (with identity check)"
for port in 8002 5666 5677; do
    pids=$(lsof -ti:"$port" 2>/dev/null || true)
    for pid in $pids; do
        if _is_fance_pid "$pid"; then
            _kill_pid_tree "$pid" "Service on port $port (PID $pid)"
        else
            echo "  Skip: port $port held by non-FAN-CE PID $pid"
        fi
    done
done

# ── Layer 3: Long-tail cleanup by PID file children ──
echo "  [Layer 3] Stale process cleanup"
# Check for any remaining processes under /tmp/fance-*.log file handles
for logfile in /tmp/fance-backend.log /tmp/fance-admin.log /tmp/fance-public.log; do
    if [ -f "$logfile" ]; then
        pids=$(lsof -t "$logfile" 2>/dev/null || true)
        for pid in $pids; do
            _kill_pid_tree "$pid" "Log holder for $logfile (PID $pid)" || true
        done
        rm -f "$logfile"
    fi
done

echo ""
if [ "$STOPPED" -eq 0 ]; then
    echo "No running FAN-CE services found."
else
    echo -e "${GREEN}All FAN-CE services stopped ($STOPPED processes).${NC}"
fi
