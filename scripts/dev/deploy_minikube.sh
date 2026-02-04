#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is not installed or not on PATH." >&2
  exit 1
fi

NAMESPACE="${NAMESPACE:-cats-dogs}"
KUSTOMIZE_DIR="${KUSTOMIZE_DIR:-k8s/overlays/dev}"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-180s}"

if [ ! -d "$KUSTOMIZE_DIR" ]; then
  echo "ERROR: kustomize directory not found at ${KUSTOMIZE_DIR}" >&2
  exit 1
fi

echo "==> Applying manifests from ${KUSTOMIZE_DIR}"
kubectl apply -k "$KUSTOMIZE_DIR" >/dev/null

echo "==> Waiting for deployment rollout"
kubectl -n "$NAMESPACE" rollout status deployment/cats-dogs-api --timeout="$ROLLOUT_TIMEOUT"

echo "==> Running in-cluster smoke test"
NAMESPACE="$NAMESPACE" ./scripts/dev/smoke_test_k8s.sh

echo "==> Deployment complete"
