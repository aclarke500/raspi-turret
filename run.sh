#!/usr/bin/env bash
git pull
set -euo pipefail
cd "$(dirname "$0")"
source venv/bin/activate
exec uvicorn main:app --host 0.0.0.0 --port 8000
