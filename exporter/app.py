"""IBM Power Fleet Observability — Prometheus Exporter.

Environment variables:
  POWER_SOURCE   simulated (default) | hmc
  SCENARIO       optional fault scenario (simulated source only)
  EXPORTER_PORT  HTTP port (default: 8000)
"""
from __future__ import annotations

import logging
import os
import sys
import time

from prometheus_client import (
    Gauge,
    Info,
    start_http_server,
    REGISTRY,
    CollectorRegistry,
)
from prometheus_client.core import GaugeMetricFamily, REGISTRY as DEFAULT_REGISTRY

from sources.base import PowerSource
from sources.simulated import SimulatedSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
log = logging.getLogger("power_exporter")

# ── metric definitions ────────────────────────────────────────────────────────

LPAR_CPU = Gauge(
    "power_lpar_cpu_utilisation",
    "CPU utilisation of an LPAR (0.0–1.0)",
    ["frame", "lpar"],
)
LPAR_ENTITLED_CORES = Gauge(
    "power_lpar_entitled_cores",
    "Entitled processing capacity assigned to the LPAR",
    ["frame", "lpar"],
)
LPAR_VPROC = Gauge(
    "power_lpar_virtual_processors",
    "Number of virtual processors assigned to the LPAR",
    ["frame", "lpar"],
)
LPAR_MEM_USED = Gauge(
    "power_lpar_memory_used_gb",
    "Memory currently in use by the LPAR (GiB)",
    ["frame", "lpar"],
)
LPAR_MEM_TOTAL = Gauge(
    "power_lpar_memory_total_gb",
    "Total memory allocated to the LPAR (GiB)",
    ["frame", "lpar"],
)
LPAR_STATE = Gauge(
    "power_lpar_state",
    "LPAR operational state: 1 = Running, 0 = other",
    ["frame", "lpar"],
)
VIOS_DISK_LATENCY = Gauge(
    "power_vios_disk_latency_ms",
    "Average disk I/O latency reported by the VIOS (ms)",
    ["frame", "vios"],
)
VIOS_NET_THROUGHPUT = Gauge(
    "power_vios_net_throughput_mbps",
    "Network throughput through the VIOS (Mbps)",
    ["frame", "vios"],
)
VIOS_STATE = Gauge(
    "power_vios_state",
    "VIOS operational state: 1 = Running, 0 = other",
    ["frame", "vios"],
)
FRAME_TOTAL_CORES = Gauge(
    "power_frame_total_cores",
    "Total physical processing cores in the frame",
    ["frame"],
)
FRAME_ALLOCATED_CORES = Gauge(
    "power_frame_allocated_cores",
    "Processing cores allocated to all LPARs in the frame",
    ["frame"],
)
SOURCE_HEALTHY = Gauge(
    "power_source_healthy",
    "1 if the data source (HMC/simulated) is reachable, 0 otherwise",
)
SCRAPE_DURATION = Gauge(
    "power_scrape_duration_seconds",
    "Time taken to collect metrics from the data source",
)
SCRAPE_ERRORS = Gauge(
    "power_scrape_errors_total",
    "Cumulative number of failed scrape attempts",
)

# ── source factory ────────────────────────────────────────────────────────────

def _build_source() -> PowerSource:
    src = os.environ.get("POWER_SOURCE", "simulated").lower()
    if src == "hmc":
        from sources.hmc import HmcSource
        log.info("Using HMC data source")
        return HmcSource()
    log.info("Using simulated data source (SCENARIO=%s)", os.environ.get("SCENARIO", "none"))
    return SimulatedSource()


# ── collection loop ───────────────────────────────────────────────────────────

def collect_and_update(source: PowerSource) -> None:
    """Pull one snapshot from source and push values into gauges."""
    start = time.time()
    try:
        SOURCE_HEALTHY.set(1 if source.is_healthy() else 0)
        frames = source.collect()

        for frame in frames:
            FRAME_TOTAL_CORES.labels(frame=frame.name).set(frame.total_cores)
            FRAME_ALLOCATED_CORES.labels(frame=frame.name).set(frame.allocated_cores)

            for lpar in frame.lpars:
                lbl = {"frame": frame.name, "lpar": lpar.name}
                LPAR_CPU.labels(**lbl).set(lpar.cpu_utilisation)
                LPAR_ENTITLED_CORES.labels(**lbl).set(lpar.entitled_cores)
                LPAR_VPROC.labels(**lbl).set(lpar.virtual_processors)
                LPAR_MEM_USED.labels(**lbl).set(lpar.memory_used_gb)
                LPAR_MEM_TOTAL.labels(**lbl).set(lpar.memory_total_gb)
                LPAR_STATE.labels(**lbl).set(1 if lpar.state == "Running" else 0)

            for vios in frame.vios_list:
                lbl = {"frame": frame.name, "vios": vios.name}
                VIOS_DISK_LATENCY.labels(**lbl).set(vios.disk_latency_ms)
                VIOS_NET_THROUGHPUT.labels(**lbl).set(vios.net_throughput_mbps)
                VIOS_STATE.labels(**lbl).set(1 if vios.state == "Running" else 0)

    except Exception as exc:
        log.exception("Error collecting metrics: %s", exc)
        SCRAPE_ERRORS.inc()
    finally:
        SCRAPE_DURATION.set(time.time() - start)


# ── entrypoint ────────────────────────────────────────────────────────────────

def main() -> None:
    port    = int(os.environ.get("EXPORTER_PORT", "8000"))
    interval = int(os.environ.get("SCRAPE_INTERVAL", "15"))
    source  = _build_source()

    log.info("Starting Power Fleet exporter on :%d (interval=%ds)", port, interval)
    start_http_server(port)

    while True:
        collect_and_update(source)
        time.sleep(interval)


if __name__ == "__main__":
    main()
