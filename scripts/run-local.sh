#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8080}

PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
  exec "$PYTHON_BIN" -m consensus_web --host "$HOST" --port "$PORT" "$@"
