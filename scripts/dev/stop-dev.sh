#!/usr/bin/env bash
# Stop FAN-CE development servers
set -euo pipefail

STOPPED=false

# Backend (port 8002)
PID=$(lsof -ti:8002 2>/dev/null || true)
if [ -n "$PID" ]; then
  kill -9 $PID 2>/dev/null && echo "已停止后端 (port 8002, PID $PID)" || true
  STOPPED=true
else
  echo "后端未运行 (port 8002)"
fi

# Frontend (port 5666)
PID=$(lsof -ti:5666 2>/dev/null || true)
if [ -n "$PID" ]; then
  kill -9 $PID 2>/dev/null && echo "已停止前端 (port 5666, PID $PID)" || true
  STOPPED=true
else
  echo "前端未运行 (port 5666)"
fi

if [ "$STOPPED" = false ]; then
  echo "没有运行中的开发服务器"
fi
