#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is not installed or not on PATH." >&2
  exit 1
fi

NAMESPACE="${NAMESPACE:-cats-dogs}"
JOB_NAME="${JOB_NAME:-cats-dogs-smoke-test}"
JOB_MANIFEST="${JOB_MANIFEST:-k8s/base/smoke-test-job.yaml}"
JOB_TIMEOUT="${JOB_TIMEOUT:-180s}"

if [ ! -f "$JOB_MANIFEST" ]; then
  echo "ERROR: job manifest not found at ${JOB_MANIFEST}" >&2
  exit 1
fi

echo "==> Running smoke test job in namespace ${NAMESPACE}"

kubectl -n "$NAMESPACE" delete job "$JOB_NAME" --ignore-not-found >/dev/null
kubectl -n "$NAMESPACE" apply -f "$JOB_MANIFEST" >/dev/null

if ! kubectl -n "$NAMESPACE" wait --for=condition=complete "job/${JOB_NAME}" --timeout="$JOB_TIMEOUT"; then
  echo "ERROR: smoke test job failed or timed out." >&2
  kubectl -n "$NAMESPACE" logs "job/${JOB_NAME}" --all-containers || true
  kubectl -n "$NAMESPACE" describe "job/${JOB_NAME}" || true
  exit 1
fi

echo "==> Smoke test job completed successfully"
kubectl -n "$NAMESPACE" logs "job/${JOB_NAME}" --all-containers || true
