# Architecture — IBM Power Fleet Observability

## Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster (Minikube)                  │
│  namespace: power-fleet                                          │
│                                                                  │
│  ┌──────────────────┐    scrape     ┌──────────────────────┐    │
│  │  power-exporter  │◄─────────────►│     Prometheus       │    │
│  │  (Python)        │  :8000/metrics│  :9090  NodePort:30090│    │
│  │                  │               │  ┌──────────────────┐│    │
│  │  SimulatedSource │               │  │  Alert Rules     ││    │
│  │  HmcSource(stub) │               │  │  power-fleet-*   ││    │
│  └──────────────────┘               │  └────────┬─────────┘│    │
│                                     └───────────┼──────────┘    │
│                                                 │ alerts        │
│                                     ┌───────────▼──────────┐    │
│                                     │    Alertmanager      │    │
│                                     │  :9093  NodePort:30093│    │
│                                     │  ┌──────┐ ┌────────┐ │    │
│                                     │  │Gmail │ │Webhook │ │    │
│                                     │  └──────┘ └────────┘ │    │
│                                     └──────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    Grafana                               │    │
│  │  :3000  NodePort:30030                                   │    │
│  │  Datasource: Prometheus (auto-provisioned)               │    │
│  │  Dashboard:  IBM Power Fleet (auto-provisioned)          │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Source Design

The exporter uses a pluggable source pattern:

```
PowerSource (ABC)
├── SimulatedSource   ← default (POWER_SOURCE=simulated)
└── HmcSource         ← skeleton for real lab (POWER_SOURCE=hmc)
```

Each source returns `List[FrameMetrics]` with nested `LparMetrics` and `ViosMetrics`.

---

## Simulated Fleet Topology

| Frame   | Total Cores | LPARs | VIOS |
|---------|-------------|-------|------|
| frame01 | 48          | 5     | 2    |
| frame02 | 32          | 5     | 2    |

### LPARs

| LPAR          | Frame   | Entitled | Mem (GiB) |
|---------------|---------|----------|-----------|
| lpar-db2-01   | frame01 | 8        | 128       |
| lpar-app-01   | frame01 | 4        | 64        |
| lpar-app-02   | frame01 | 4        | 64        |
| lpar-web-01   | frame01 | 2        | 32        |
| lpar-batch-01 | frame01 | 6        | 96        |
| lpar-sap-01   | frame02 | 10       | 256       |
| lpar-sap-02   | frame02 | 10       | 256       |
| lpar-mq-01    | frame02 | 2        | 32        |
| lpar-ai-01    | frame02 | 6        | 128       |
| lpar-dev-01   | frame02 | 1        | 16        |

---

## Metrics Emitted

| Metric | Type | Labels |
|--------|------|--------|
| `power_lpar_cpu_utilisation` | Gauge | frame, lpar |
| `power_lpar_entitled_cores` | Gauge | frame, lpar |
| `power_lpar_virtual_processors` | Gauge | frame, lpar |
| `power_lpar_memory_used_gb` | Gauge | frame, lpar |
| `power_lpar_memory_total_gb` | Gauge | frame, lpar |
| `power_lpar_state` | Gauge | frame, lpar, state |
| `power_vios_disk_latency_ms` | Gauge | frame, vios |
| `power_vios_net_throughput_mbps` | Gauge | frame, vios |
| `power_vios_state` | Gauge | frame, vios, state |
| `power_frame_total_cores` | Gauge | frame |
| `power_frame_allocated_cores` | Gauge | frame |
| `power_source_healthy` | Gauge | — |
| `power_scrape_duration_seconds` | Gauge | — |
| `power_scrape_errors_total` | Gauge | — |

---

## Alert Rules Summary

| Alert | Condition | Severity |
|-------|-----------|----------|
| LparHighCpu | CPU > 85 % for 2 m | warning |
| LparCriticalCpu | CPU > 95 % for 1 m | critical |
| LparHighMemory | mem/total > 90 % for 5 m | warning |
| LparDown | state ≠ Running | critical |
| FrameOvercommit | allocated/total > 100 % for 1 m | warning |
| FrameHighOvercommit | allocated/total > 110 % for 1 m | critical |
| ViosHighDiskLatency | latency > 50 ms for 2 m | warning |
| ViosCriticalDiskLatency | latency > 150 ms for 1 m | critical |
| ViosDown | state ≠ Running | critical |
| PowerSourceUnhealthy | source_healthy == 0 for 1 m | critical |
| ExporterDown | up == 0 for 1 m | critical |

---

## Security Notes

- Gmail App Password is stored in a Kubernetes `Secret` (`alertmanager-gmail`).
- The Secret is mounted as a file — never passed as an environment variable.
- The Secret is not part of any manifest in the repository. `scripts/demo.sh` creates a placeholder only if it does not exist, and `scripts/create_gmail_secret.sh` stores the real password straight into the cluster.
- The exporter runs as `nobody` (UID 65534) with `runAsNonRoot: true`.
