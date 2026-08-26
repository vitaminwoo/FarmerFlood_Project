#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec .venv/bin/uvicorn api.app:app --host 127.0.0.1 --port "${FLOOD_WORKER_PORT:-8091}"
