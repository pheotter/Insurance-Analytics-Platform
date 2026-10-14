#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

exec "${PYTHON_BIN:-${ROOT_DIR}/env/bin/python}" -m uvicorn \
  actuarial_api.main:app \
  --host "${ACTUARIAL_API_HOST:-0.0.0.0}" \
  --port "${ACTUARIAL_API_PORT:-8000}" \
  --reload
