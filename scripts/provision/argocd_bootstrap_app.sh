#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is not installed or not on PATH." >&2
  exit 1
fi

NAMESPACE="${ARGOCD_NAMESPACE:-argocd}"
APP_MANIFEST="${APP_MANIFEST:-argocd/application.yaml}"

if [ ! -f "$APP_MANIFEST" ]; then
  echo "ERROR: Application manifest not found at ${APP_MANIFEST}" >&2
  exit 1
fi

if ! kubectl get crd applications.argoproj.io >/dev/null 2>&1; then
  echo "ERROR: Argo CD CRDs not found. Run scripts/provision/argocd_install.sh first." >&2
  exit 1
fi

echo "==> Applying Argo CD Application manifest"
kubectl -n "$NAMESPACE" apply -f "$APP_MANIFEST"

kubectl -n "$NAMESPACE" get applications.argoproj.io cats-dogs >/dev/null

echo "==> Argo CD Application is registered"
