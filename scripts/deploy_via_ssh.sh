#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_PORT="${DEPLOY_PORT:-22}"
RELEASE_ID="${RELEASE_ID:-$(date -u +%Y%m%d%H%M%S)}"
ARTIFACT_PATH="${DEPLOY_ARTIFACT:-}"

required_vars=(DEPLOY_HOST DEPLOY_USER DEPLOY_PATH)
for name in "${required_vars[@]}"; do
    if [[ -z "${!name:-}" ]]; then
        echo "Missing required environment variable: ${name}" >&2
        exit 2
    fi
done

if [[ -z "${ARTIFACT_PATH}" ]]; then
    ARTIFACT_PATH="$(ls -t "${ROOT_DIR}"/dist/insurance-actuarial-platform-*.tar.gz | head -n 1)"
fi

if [[ ! -f "${ARTIFACT_PATH}" ]]; then
    echo "Deployment artifact not found: ${ARTIFACT_PATH}" >&2
    exit 2
fi

REMOTE_RELEASE_DIR="${DEPLOY_PATH}/releases/${RELEASE_ID}"
REMOTE_ARTIFACT="/tmp/$(basename "${ARTIFACT_PATH}")"
SSH_TARGET="${DEPLOY_USER}@${DEPLOY_HOST}"
SSH_OPTS=(-p "${DEPLOY_PORT}" -o StrictHostKeyChecking=accept-new)

ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "mkdir -p '${DEPLOY_PATH}/releases'"
scp -P "${DEPLOY_PORT}" "${ARTIFACT_PATH}" "${SSH_TARGET}:${REMOTE_ARTIFACT}"
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "
    set -Eeuo pipefail
    mkdir -p '${REMOTE_RELEASE_DIR}'
    tar -xzf '${REMOTE_ARTIFACT}' -C '${REMOTE_RELEASE_DIR}'
    ln -sfn '${REMOTE_RELEASE_DIR}' '${DEPLOY_PATH}/current'
    rm -f '${REMOTE_ARTIFACT}'
"

echo "Deployed ${ARTIFACT_PATH} to ${SSH_TARGET}:${REMOTE_RELEASE_DIR}"
