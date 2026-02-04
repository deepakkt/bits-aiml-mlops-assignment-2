#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v minikube >/dev/null 2>&1; then
  echo "ERROR: minikube is not installed or not on PATH." >&2
  exit 1
fi

PROFILE="${MINIKUBE_PROFILE:-minikube}"
START_ARGS="${MINIKUBE_START_ARGS:-}"
ADDONS="${MINIKUBE_ADDONS:-}"

status_out="$(minikube status -p "$PROFILE" 2>/dev/null || true)"
if echo "$status_out" | grep -q "host: Running" && \
   echo "$status_out" | grep -q "kubelet: Running" && \
   echo "$status_out" | grep -q "apiserver: Running"; then
  echo "==> Minikube profile '${PROFILE}' is already running"
else
  echo "==> Starting Minikube profile '${PROFILE}'"
  minikube start -p "$PROFILE" $START_ARGS
fi

if [ -n "$ADDONS" ]; then
  echo "==> Enabling Minikube addons: ${ADDONS}"
  for addon in $ADDONS; do
    minikube -p "$PROFILE" addons enable "$addon"
  done
fi

# Ensure kubectl context points to the selected profile
kubectl config use-context "$PROFILE" >/dev/null

echo "==> Minikube is ready"
