#!/usr/bin/env bash
# scripts/inject_scenario.sh
# Inject or clear a fault scenario into the running power-exporter.
#
# Usage:
#   bash scripts/inject_scenario.sh <scenario>
#   bash scripts/inject_scenario.sh clear
#
# Scenarios:
#   cpu_saturation      lpar-db2-01 pegged at ~98 % CPU
#   memory_leak         lpar-app-01 memory grows over time
#   lpar_down           lpar-web-01 flips to Not Activated
#   frame_overcommit    frame01 committed cores > physical
#   vios_disk_latency   vios-01* disk latency spikes to ~180 ms
#   hmc_unreachable     source reports unhealthy
#   clear               remove active scenario (baseline)
#
set -euo pipefail

NAMESPACE="power-fleet"
DEPLOYMENT="power-exporter"
VALID_SCENARIOS="cpu_saturation memory_leak lpar_down frame_overcommit vios_disk_latency hmc_unreachable clear"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

SCENARIO="${1:-}"
[[ -z "$SCENARIO" ]] && error "Usage: $0 <scenario|clear>  — valid: $VALID_SCENARIOS"
echo "$VALID_SCENARIOS" | grep -qw "$SCENARIO" || error "Unknown scenario '$SCENARIO'. Valid: $VALID_SCENARIOS"

if [[ "$SCENARIO" == "clear" ]]; then
  VALUE=""
  info "Clearing scenario — returning exporter to baseline"
else
  VALUE="$SCENARIO"
  info "Injecting scenario: $SCENARIO"
fi

kubectl set env deployment/"$DEPLOYMENT" \
  -n "$NAMESPACE" \
  SCENARIO="$VALUE"

info "Waiting for rollout …"
kubectl rollout status deployment/"$DEPLOYMENT" -n "$NAMESPACE" --timeout=60s

MINIKUBE_IP=$(minikube ip 2>/dev/null || echo "localhost")
info "Done. Check metrics with: kubectl port-forward -n ${NAMESPACE} svc/power-exporter 8000:8000"
info "Prometheus targets   : http://${MINIKUBE_IP}:30090/targets"
info "Grafana dashboard    : http://${MINIKUBE_IP}:30030"
