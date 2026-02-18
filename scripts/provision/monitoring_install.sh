#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is not installed or not on PATH." >&2
  exit 1
fi

if ! command -v helm >/dev/null 2>&1; then
  echo "ERROR: helm is not installed or not on PATH." >&2
  exit 1
fi

MONITORING_NAMESPACE="${MONITORING_NAMESPACE:-monitoring}"
PROM_STACK_RELEASE="${PROM_STACK_RELEASE:-kube-prometheus-stack}"
PROM_STACK_CHART="${PROM_STACK_CHART:-prometheus-community/kube-prometheus-stack}"
PROM_STACK_VALUES="${PROM_STACK_VALUES:-monitoring/kube-prometheus-stack-values.yaml}"
PROM_STACK_TIMEOUT="${PROM_STACK_TIMEOUT:-600s}"
PROM_STACK_CHART_VERSION="${PROM_STACK_CHART_VERSION:-}"
SERVICE_MONITOR_MANIFEST="${SERVICE_MONITOR_MANIFEST:-monitoring/servicemonitor-cats-dogs.yaml}"
GRAFANA_DASHBOARD_KUSTOMIZE_DIR="${GRAFANA_DASHBOARD_KUSTOMIZE_DIR:-monitoring/grafana}"

if [ ! -f "$PROM_STACK_VALUES" ]; then
  echo "ERROR: Prometheus stack values file not found at ${PROM_STACK_VALUES}" >&2
  exit 1
fi

if [ ! -f "$SERVICE_MONITOR_MANIFEST" ]; then
  echo "ERROR: ServiceMonitor manifest not found at ${SERVICE_MONITOR_MANIFEST}" >&2
  exit 1
fi

if [ ! -f "$GRAFANA_DASHBOARD_KUSTOMIZE_DIR/kustomization.yaml" ]; then
  echo "ERROR: Grafana dashboard kustomization not found in ${GRAFANA_DASHBOARD_KUSTOMIZE_DIR}" >&2
  exit 1
fi

if ! helm repo list | awk 'NR>1 {print $1}' | grep -qx 'prometheus-community'; then
  echo "==> Adding Helm repo prometheus-community"
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
fi

echo "==> Updating Helm repositories"
helm repo update >/dev/null

echo "==> Installing/Upgrading ${PROM_STACK_RELEASE} in namespace ${MONITORING_NAMESPACE}"
helm_args=(
  upgrade --install "$PROM_STACK_RELEASE" "$PROM_STACK_CHART"
  --namespace "$MONITORING_NAMESPACE"
  --create-namespace
  --wait
  --timeout "$PROM_STACK_TIMEOUT"
  -f "$PROM_STACK_VALUES"
)
if [ -n "$PROM_STACK_CHART_VERSION" ]; then
  helm_args+=(--version "$PROM_STACK_CHART_VERSION")
fi
helm "${helm_args[@]}"

echo "==> Waiting for ServiceMonitor CRD"
kubectl wait --for=condition=Established crd/servicemonitors.monitoring.coreos.com --timeout="$PROM_STACK_TIMEOUT"

service_monitor_namespace="$(awk '/^[[:space:]]*namespace:[[:space:]]*/ {print $2; exit}' "$SERVICE_MONITOR_MANIFEST")"
service_monitor_namespace="${service_monitor_namespace:-default}"
if ! kubectl get namespace "$service_monitor_namespace" >/dev/null 2>&1; then
  echo "==> Creating namespace ${service_monitor_namespace} for ServiceMonitor target"
  kubectl create namespace "$service_monitor_namespace"
fi

echo "==> Applying ServiceMonitor for cats-dogs-api"
kubectl apply -f "$SERVICE_MONITOR_MANIFEST"

echo "==> Applying Grafana dashboard ConfigMap"
kubectl apply -k "$GRAFANA_DASHBOARD_KUSTOMIZE_DIR"

echo "==> Monitoring stack ready"
echo "Grafana port-forward:"
echo "  kubectl -n ${MONITORING_NAMESPACE} port-forward svc/${PROM_STACK_RELEASE}-grafana 3000:80"
echo "Prometheus port-forward:"
echo "  kubectl -n ${MONITORING_NAMESPACE} port-forward svc/${PROM_STACK_RELEASE}-kube-prometheus-prometheus 9090:9090"
