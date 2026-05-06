#!/usr/bin/env bash
# Stop FAN-CE development servers
set -euo pipefail

STOPPED=false

# Backend (port 8002)
PID=$(lsof -ti:8002 2>/dev/null || true)
if [ -n "$PID" ]; then
  kill -9 $PID 2>/dev/null && echo "Stopped backend (port 8002, PID $PID)" || true
  STOPPED=true
else
  echo "Backend not running (port 8002)"
fi

# Admin frontend (port 5666)
PID=$(lsof -ti:5666 2>/dev/null || true)
if [ -n "$PID" ]; then
  kill -9 $PID 2>/dev/null && echo "Stopped admin-web (port 5666, PID $PID)" || true
  STOPPED=true
else
  echo "Admin-web not running (port 5666)"
fi

# Public web (port 5677)
PID=$(lsof -ti:5677 2>/dev/null || true)
if [ -n "$PID" ]; then
  kill -9 $PID 2>/dev/null && echo "Stopped public-web (port 5677, PID $PID)" || true
  STOPPED=true
else
  echo "Public-web not running (port 5677)"
fi

if [ "$STOPPED" = false ]; then
  echo "No running dev servers"
fi
