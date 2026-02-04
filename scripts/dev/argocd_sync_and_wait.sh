#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v argocd >/dev/null 2>&1; then
  echo "ERROR: argocd CLI is not installed or not on PATH." >&2
  echo "Install it from https://argo-cd.readthedocs.io and login before running this script." >&2
  exit 1
fi

APP_NAME="${ARGOCD_APP:-cats-dogs}"
TIMEOUT="${ARGOCD_TIMEOUT:-300}"
ARGOCD_OPTS="${ARGOCD_OPTS:-}"
DO_SYNC="${ARGOCD_DO_SYNC:-true}"

if ! argocd $ARGOCD_OPTS account get-user-info >/dev/null 2>&1; then
  echo "ERROR: Not logged in to Argo CD or insufficient permissions." >&2
  echo "Ensure port-forward is running and login:" >&2
  echo "  kubectl -n argocd port-forward svc/argocd-server 8080:443" >&2
  echo "  kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 --decode; echo" >&2
  echo "  argocd login localhost:8080 --username admin --password <password> --insecure" >&2
  exit 1
fi

if [ "$DO_SYNC" = "true" ]; then
  echo "==> Triggering Argo CD sync for app ${APP_NAME}"
  argocd $ARGOCD_OPTS app sync "$APP_NAME"
fi

echo "==> Waiting for app ${APP_NAME} to be Synced/Healthy"
argocd $ARGOCD_OPTS app wait "$APP_NAME" --sync --health --timeout "$TIMEOUT"

echo "==> Argo CD app is Synced and Healthy"
