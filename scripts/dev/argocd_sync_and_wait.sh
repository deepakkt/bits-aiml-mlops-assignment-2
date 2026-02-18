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

print_app_debug() {
  echo "==> Argo CD app status snapshot"
  argocd $ARGOCD_OPTS app get "$APP_NAME" || true
  echo "==> Argo CD app history"
  argocd $ARGOCD_OPTS app history "$APP_NAME" || true
}

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
  if ! argocd $ARGOCD_OPTS app sync "$APP_NAME"; then
    echo "ERROR: Argo CD sync failed for app ${APP_NAME}." >&2
    print_app_debug
    exit 1
  fi
fi

echo "==> Waiting for app ${APP_NAME} to be Synced/Healthy"
if ! argocd $ARGOCD_OPTS app wait "$APP_NAME" --sync --health --timeout "$TIMEOUT"; then
  echo "ERROR: App ${APP_NAME} did not become Synced/Healthy (or hook failed)." >&2
  print_app_debug
  exit 1
fi

echo "==> Argo CD app is Synced and Healthy"
