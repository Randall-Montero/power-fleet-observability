#!/usr/bin/env bash
# scripts/demo.sh
# Full end-to-end demo for IBM Power Fleet Observability on Minikube.
#
# Usage:
#   bash scripts/demo.sh            # deploy everything
#   bash scripts/demo.sh --teardown # remove namespace and reset
#
set -euo pipefail

NAMESPACE="power-fleet"
IMAGE_NAME="power-fleet-observability"
IMAGE_TAG="latest"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
section() { echo -e "\n${YELLOW}═══ $* ═══${NC}"; }

# ── teardown ──────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--teardown" ]]; then
  section "Teardown"
  kubectl delete namespace "$NAMESPACE" --ignore-not-found
  info "Namespace $NAMESPACE deleted. Done."
  exit 0
fi

# ── prerequisites ─────────────────────────────────────────────────────────────
section "Checking prerequisites"
for cmd in minikube kubectl docker; do
  command -v "$cmd" >/dev/null 2>&1 || error "$cmd not found in PATH"
  info "$cmd ✓"
done

# ── Minikube ──────────────────────────────────────────────────────────────────
section "Starting Minikube"
if ! minikube status | grep -q "Running"; then
  minikube start --cpus=4 --memory=6144 --driver=docker
else
  info "Minikube already running"
fi

# ── Build image locally and load it into Minikube ─────────────────────────────
# Works with any Minikube runtime (docker or containerd) and on Windows,
# unlike `minikube docker-env`.
section "Building exporter image"
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .
minikube image load "${IMAGE_NAME}:${IMAGE_TAG}"
info "Image ${IMAGE_NAME}:${IMAGE_TAG} built and loaded into Minikube"

# ── Deploy manifests ──────────────────────────────────────────────────────────
section "Applying Kubernetes manifests"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/exporter.yaml
kubectl apply -f k8s/prometheus-config.yaml
# Alert rules: single source of truth is monitoring/rules/power-fleet-alerts.yml (also linted in CI)
kubectl create configmap prometheus-rules -n "$NAMESPACE" \
  --from-file=power-fleet-alerts.yml=monitoring/rules/power-fleet-alerts.yml \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/prometheus.yaml
kubectl apply -f k8s/webhook-sink.yaml

# Gmail Secret: create a placeholder ONLY if it does not exist yet, so a real
# password set with scripts/create_gmail_secret.sh is never overwritten.
if ! kubectl get secret alertmanager-gmail -n "$NAMESPACE" >/dev/null 2>&1; then
  kubectl create secret generic alertmanager-gmail -n "$NAMESPACE" \
    --from-literal=gmail_password="REPLACE_WITH_APP_PASSWORD"
  warn "Gmail Secret is a placeholder. Run: bash scripts/create_gmail_secret.sh"
fi
kubectl apply -f k8s/alertmanager.yaml
# Grafana dashboard: single source of truth is grafana/dashboards/power-fleet.json
kubectl create configmap grafana-dashboards -n "$NAMESPACE" \
  --from-file=power-fleet.json=grafana/dashboards/power-fleet.json \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/grafana.yaml

# ── Wait for rollout ──────────────────────────────────────────────────────────
section "Waiting for deployments to be ready"
for deploy in power-exporter prometheus webhook-sink alertmanager grafana; do
  info "Waiting for $deploy …"
  kubectl rollout status deployment/"$deploy" -n "$NAMESPACE" --timeout=120s
done

# ── Print access URLs ─────────────────────────────────────────────────────────
section "Access URLs"
MINIKUBE_IP=$(minikube ip)
echo -e "  Prometheus       : http://${MINIKUBE_IP}:30090"
echo -e "  Grafana          : http://${MINIKUBE_IP}:30030  (admin/admin)"
echo -e "  Alertmanager     : http://${MINIKUBE_IP}:30093"
echo -e "  Exporter metrics : kubectl port-forward -n ${NAMESPACE} svc/power-exporter 8000:8000"
echo -e "                     then http://localhost:8000/metrics"
echo -e "  Webhook sink log : kubectl logs -n ${NAMESPACE} deploy/webhook-sink"

info "Demo deployed successfully 🎉"
info "Inject a scenario with:  bash scripts/inject_scenario.sh cpu_saturation"
