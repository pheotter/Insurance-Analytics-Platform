#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DBT_PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="$(cd "${DBT_PROJECT_DIR}/.." && pwd)"
DBT_BIN="${PROJECT_ROOT}/env/bin/dbt"

# Prefer one shared repository-level .env, but support the current location
# until the environment files have been consolidated.
ENV_FILE="${PROJECT_ROOT}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
    ENV_FILE="${DBT_PROJECT_DIR}/.env"
fi

if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Missing environment file: ${PROJECT_ROOT}/.env" >&2
    exit 1
fi

if [[ ! -x "${DBT_BIN}" ]]; then
    echo "dbt executable not found: ${DBT_BIN}" >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

cd "${DBT_PROJECT_DIR}"
exec "${DBT_BIN}" "$@"
