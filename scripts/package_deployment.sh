#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/dist"
VERSION="${GITHUB_SHA:-$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || date -u +%Y%m%d%H%M%S)}"
ARTIFACT_NAME="insurance-actuarial-platform-${VERSION}.tar.gz"
ARTIFACT_PATH="${BUILD_DIR}/${ARTIFACT_NAME}"

mkdir -p "${BUILD_DIR}"
rm -f "${ARTIFACT_PATH}"

cd "${ROOT_DIR}"

tar \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.git' \
    --exclude='.env' \
    --exclude='env' \
    --exclude='logs' \
    --exclude='dist' \
    --exclude='data_pipeline/.env' \
    --exclude='data_pipeline/logs' \
    --exclude='data_pipeline/target' \
    --exclude='data_pipeline/secrets' \
    --exclude='airflow/.env' \
    --exclude='airflow/logs' \
    --exclude='airflow/review_packets' \
    --exclude='secrets' \
    -czf "${ARTIFACT_PATH}" \
    README.md \
    pyproject.toml \
    scripts \
    airflow/dags \
    airflow/requirements.txt \
    data_pipeline/dbt_project.yml \
    data_pipeline/profiles.yml \
    data_pipeline/packages.yml \
    data_pipeline/macros \
    data_pipeline/models \
    data_pipeline/seeds \
    data_pipeline/snapshots \
    data_pipeline/tests \
    data_pipeline/analyses \
    data_pipeline/scripts \
    actuarial_engine \
    actuarial_workflow \
    actuarial_api \
    platform_common \
    streamlit_app \
    docs

echo "${ARTIFACT_PATH}"
