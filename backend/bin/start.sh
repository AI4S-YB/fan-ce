#!/usr/bin/env bash
alembic_env="/usr/local/bin/alembic"
PYTHON_ENV="/usr/bin/python3"
WORKER_DIR="/data/fan_ce"
WORKER_USER="root"

export PATH=$PATH:$PYTHON_ENV


case "$1" in
  start|1)
  ps aux |grep -E "multiprocessing|main.py" |grep -v grep |awk '{print $2}'|xargs kill -9
  cd $WORKER_DIR || exit
  nohup $PYTHON_ENV $WORKER_DIR/main.py &
    ;;
  db_init)
    $alembic_env revision  --autogenerate  -m 'one';$alembic_env upgrade head
    ;;
  *)
    echo $"Usage: $0 {db_init|} {start}"
    ;;
esac