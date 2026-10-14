#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

exec "${STREAMLIT_BIN:-${ROOT_DIR}/env/bin/streamlit}" run \
  streamlit_app/app.py \
  --server.port "${STREAMLIT_PORT:-8501}"
