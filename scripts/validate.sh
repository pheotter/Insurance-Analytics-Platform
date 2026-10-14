#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [[ -z "${DBT_BIN:-}" ]]; then
    if [[ -x "${ROOT_DIR}/env/bin/dbt" ]]; then
        DBT_BIN="${ROOT_DIR}/env/bin/dbt"
    else
        DBT_BIN="dbt"
    fi
fi
MODE="${1:-all}"

export DBT_PROFILES_DIR="${DBT_PROFILES_DIR:-${ROOT_DIR}/data_pipeline}"
export SNOWFLAKE_ACCOUNT="${SNOWFLAKE_ACCOUNT:-ci-placeholder}"
export SNOWFLAKE_USER="${SNOWFLAKE_USER:-ci-placeholder}"
export SNOWFLAKE_ROLE="${SNOWFLAKE_ROLE:-ci-placeholder}"
export SNOWFLAKE_DATABASE="${SNOWFLAKE_DATABASE:-DBT_DB}"
export SNOWFLAKE_WAREHOUSE="${SNOWFLAKE_WAREHOUSE:-CI_WH}"
export SNOWFLAKE_SCHEMA="${SNOWFLAKE_SCHEMA:-DBT_SCHEMA}"
export SNOWFLAKE_PRIVATE_KEY_PATH="${SNOWFLAKE_PRIVATE_KEY_PATH:-${ROOT_DIR}/secrets/ci_placeholder_key.pem}"

ensure_placeholder_private_key() {
    if [[ "${SNOWFLAKE_PRIVATE_KEY_PATH}" == "${ROOT_DIR}/secrets/ci_placeholder_key.pem" \
        && ! -f "${SNOWFLAKE_PRIVATE_KEY_PATH}" ]]; then
        mkdir -p "$(dirname "${SNOWFLAKE_PRIVATE_KEY_PATH}")"
        openssl genrsa -out "${SNOWFLAKE_PRIVATE_KEY_PATH}" 2048 >/dev/null 2>&1
        chmod 600 "${SNOWFLAKE_PRIVATE_KEY_PATH}"
    fi
}

run_python_checks() {
    "${PYTHON_BIN}" -m compileall -q \
        "${ROOT_DIR}/actuarial_engine" \
        "${ROOT_DIR}/actuarial_workflow" \
        "${ROOT_DIR}/actuarial_api" \
        "${ROOT_DIR}/platform_common" \
        "${ROOT_DIR}/airflow/dags"

    "${PYTHON_BIN}" -m pytest
}

run_dbt_static_checks() {
    ensure_placeholder_private_key
    cd "${ROOT_DIR}/data_pipeline"
    "${DBT_BIN}" deps
    "${DBT_BIN}" parse
    "${DBT_BIN}" compile --no-populate-cache --empty --select \
        stg_policy \
        stg_policy_risk_unit \
        stg_policy_coverage \
        stg_premium_transaction \
        stg_claim \
        stg_claim_transaction \
        tableau_pricing_dashboard \
        tableau_triangle_diagnostics \
        tableau_control_dashboard
}

run_dbt_warehouse_checks() {
    ensure_placeholder_private_key
    cd "${ROOT_DIR}/data_pipeline"
    "${DBT_BIN}" build --select \
        stg_policy \
        stg_policy_risk_unit \
        stg_policy_coverage \
        stg_premium_transaction \
        stg_claim \
        stg_claim_transaction
}

case "${MODE}" in
    python)
        run_python_checks
        ;;
    dbt-static)
        run_dbt_static_checks
        ;;
    dbt-build)
        run_dbt_warehouse_checks
        ;;
    all)
        run_python_checks
        run_dbt_static_checks
        ;;
    *)
        echo "Usage: $0 [python|dbt-static|dbt-build|all]" >&2
        exit 2
        ;;
esac
