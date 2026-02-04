#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is not installed or not on PATH." >&2
  exit 1
fi

NAMESPACE="${ARGOCD_NAMESPACE:-argocd}"
MANIFEST_URL="${ARGOCD_MANIFEST_URL:-https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml}"
TIMEOUT="${ARGOCD_TIMEOUT:-300s}"

if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
  echo "==> Creating namespace ${NAMESPACE}"
  kubectl create namespace "$NAMESPACE"
fi

echo "==> Installing/Updating Argo CD from ${MANIFEST_URL}"
# Use server-side apply to avoid the "annotations too long" error on CRDs.
# If this conflicts with a prior client-side apply, retry with --force-conflicts.
if ! kubectl -n "$NAMESPACE" apply --server-side --field-manager=argocd-install -f "$MANIFEST_URL"; then
  echo "==> Server-side apply conflicted with existing field managers; retrying with --force-conflicts"
  kubectl -n "$NAMESPACE" apply --server-side --force-conflicts --field-manager=argocd-install -f "$MANIFEST_URL"
fi

# Wait for CRDs to be established
kubectl wait --for=condition=Established crd/applications.argoproj.io --timeout="$TIMEOUT"

# Ensure admin has full RBAC (some clusters may have a missing admin binding).
if kubectl -n "$NAMESPACE" get configmap argocd-rbac-cm >/dev/null 2>&1; then
  policy_csv="$(kubectl -n "$NAMESPACE" get configmap argocd-rbac-cm -o jsonpath='{.data.policy\.csv}' 2>/dev/null || true)"
  if ! printf '%s' "$policy_csv" | grep -q 'g, admin, role:admin'; then
    echo "==> Ensuring Argo CD admin has role:admin"
    if [ -n "$policy_csv" ]; then
      policy_csv="${policy_csv}"$'\n'"g, admin, role:admin"
    else
      policy_csv="g, admin, role:admin"
    fi
  fi

  rbac_default="${ARGOCD_RBAC_DEFAULT_ROLE:-role:admin}"
  echo "==> Setting Argo CD RBAC default role to ${rbac_default}"

  patch_json="$(POLICY_CSV="$policy_csv" POLICY_DEFAULT="$rbac_default" python3 - <<'PY'
import json
import os

policy_csv = os.environ.get("POLICY_CSV", "")
policy_default = os.environ.get("POLICY_DEFAULT", "role:admin")
print(json.dumps({"data": {"policy.csv": policy_csv, "policy.default": policy_default}}))
PY
)"
  kubectl -n "$NAMESPACE" patch configmap argocd-rbac-cm --type merge -p "$patch_json"

  # Some installs read RBAC settings from argocd-cm instead.
  if kubectl -n "$NAMESPACE" get configmap argocd-cm >/dev/null 2>&1; then
    patch_json="$(POLICY_CSV="$policy_csv" POLICY_DEFAULT="$rbac_default" python3 - <<'PY'
import json
import os

policy_csv = os.environ.get("POLICY_CSV", "")
policy_default = os.environ.get("POLICY_DEFAULT", "role:admin")
print(json.dumps({"data": {"rbac.policy.csv": policy_csv, "rbac.policy.default": policy_default}}))
PY
)"
    kubectl -n "$NAMESPACE" patch configmap argocd-cm --type merge -p "$patch_json"
  fi

  kubectl -n "$NAMESPACE" rollout restart deployment/argocd-server >/dev/null 2>&1 || true
else
  echo "WARN: argocd-rbac-cm not found; skipping RBAC check."
fi

# Wait for core deployments to be ready
for deployment in argocd-server argocd-repo-server; do
  echo "==> Waiting for deployment/${deployment}"
  kubectl -n "$NAMESPACE" rollout status "deployment/${deployment}" --timeout="$TIMEOUT"
done

# Controller can be a deployment or a statefulset depending on Argo CD version.
if kubectl -n "$NAMESPACE" get deployment argocd-application-controller >/dev/null 2>&1; then
  echo "==> Waiting for deployment/argocd-application-controller"
  kubectl -n "$NAMESPACE" rollout status deployment/argocd-application-controller --timeout="$TIMEOUT"
elif kubectl -n "$NAMESPACE" get statefulset argocd-application-controller >/dev/null 2>&1; then
  echo "==> Waiting for statefulset/argocd-application-controller"
  kubectl -n "$NAMESPACE" rollout status statefulset/argocd-application-controller --timeout="$TIMEOUT"
else
  echo "ERROR: argocd-application-controller not found as Deployment or StatefulSet." >&2
  kubectl -n "$NAMESPACE" get deployments,statefulsets >&2 || true
  exit 1
fi

# dex is optional in some installs, so only wait if present
if kubectl -n "$NAMESPACE" get deployment argocd-dex-server >/dev/null 2>&1; then
  echo "==> Waiting for deployment/argocd-dex-server"
  kubectl -n "$NAMESPACE" rollout status deployment/argocd-dex-server --timeout="$TIMEOUT"
fi

echo "==> Argo CD is installed and ready"
