"""Simulated IBM Power fleet data source.

Generates realistic metric values for:
  - 2 frames  (frame01, frame02)
  - 5 LPARs per frame
  - 2 VIOS per frame

Injects anomaly scenarios via the SCENARIO environment variable.
Supported scenarios:
  cpu_saturation      – one LPAR pegged at 98 % CPU
  memory_leak         – one LPAR memory grows over time
  lpar_down           – one LPAR flips to "Not Activated"
  frame_overcommit    – allocated cores exceed total
  vios_disk_latency   – VIOS disk latency spikes
  hmc_unreachable     – source reports unhealthy (is_healthy → False)
"""
from __future__ import annotations

import math
import os
import random
import time
from typing import List

from .base import FrameMetrics, LparMetrics, PowerSource, ViosMetrics

# ── fixed topology ────────────────────────────────────────────────────────────
_FRAMES = [
    {
        "name": "frame01",
        "total_cores": 48.0,
        "lpars": [
            {"name": "lpar-db2-01",   "entitled": 8.0,  "vproc": 16, "mem_gb": 128.0},
            {"name": "lpar-app-01",   "entitled": 4.0,  "vproc": 8,  "mem_gb": 64.0},
            {"name": "lpar-app-02",   "entitled": 4.0,  "vproc": 8,  "mem_gb": 64.0},
            {"name": "lpar-web-01",   "entitled": 2.0,  "vproc": 4,  "mem_gb": 32.0},
            {"name": "lpar-batch-01", "entitled": 6.0,  "vproc": 12, "mem_gb": 96.0},
        ],
        "vios": [
            {"name": "vios-01a"},
            {"name": "vios-01b"},
        ],
    },
    {
        "name": "frame02",
        "total_cores": 32.0,
        "lpars": [
            {"name": "lpar-sap-01",   "entitled": 10.0, "vproc": 20, "mem_gb": 256.0},
            {"name": "lpar-sap-02",   "entitled": 10.0, "vproc": 20, "mem_gb": 256.0},
            {"name": "lpar-mq-01",    "entitled": 2.0,  "vproc": 4,  "mem_gb": 32.0},
            {"name": "lpar-ai-01",    "entitled": 6.0,  "vproc": 12, "mem_gb": 128.0},
            {"name": "lpar-dev-01",   "entitled": 1.0,  "vproc": 2,  "mem_gb": 16.0},
        ],
        "vios": [
            {"name": "vios-02a"},
            {"name": "vios-02b"},
        ],
    },
]

# leaky LPAR target (memory grows while the scenario is active)
_LEAK_LPAR = "lpar-app-01"
_LEAK_FRAME = "frame01"
_LEAK_GB_PER_MIN = 6.0   # fast enough to cross the 90 % alert threshold in a demo


def _jitter(base: float, pct: float = 0.05) -> float:
    """Add ±pct white noise to base."""
    return base * (1.0 + random.uniform(-pct, pct))


class SimulatedSource(PowerSource):
    """Fully in-process simulation — no external dependencies."""

    def __init__(self) -> None:
        self._scenario: str = os.environ.get("SCENARIO", "")
        self._leak_started_at: float | None = None

    # ── public API ────────────────────────────────────────────────────────────

    def collect(self) -> List[FrameMetrics]:
        self._scenario = os.environ.get("SCENARIO", "")
        if self._scenario == "memory_leak":
            if self._leak_started_at is None:
                self._leak_started_at = time.time()
        else:
            self._leak_started_at = None
        frames: List[FrameMetrics] = []
        for fd in _FRAMES:
            lpars = [self._build_lpar(l, fd["name"]) for l in fd["lpars"]]
            vios  = [self._build_vios(v, fd["name"]) for v in fd["vios"]]
            allocated = sum(l.entitled_cores for l in lpars)

            if self._scenario == "frame_overcommit" and fd["name"] == "frame01":
                allocated = fd["total_cores"] * 1.15   # 115 % committed

            frames.append(
                FrameMetrics(
                    name=fd["name"],
                    total_cores=fd["total_cores"],
                    allocated_cores=allocated,
                    lpars=lpars,
                    vios_list=vios,
                )
            )
        return frames

    def is_healthy(self) -> bool:
        if os.environ.get("SCENARIO") == "hmc_unreachable":
            return False
        return True

    # ── builders ──────────────────────────────────────────────────────────────

    def _build_lpar(self, cfg: dict, frame: str) -> LparMetrics:
        name = cfg["name"]
        cpu  = _jitter(0.35)          # baseline 35 % utilisation
        mem  = _jitter(cfg["mem_gb"] * 0.60)
        state = "Running"

        # --- scenario overrides ---
        scenario = self._scenario

        if scenario == "cpu_saturation" and name == "lpar-db2-01":
            cpu = _jitter(0.98, 0.01)

        if scenario == "memory_leak" and name == _LEAK_LPAR and frame == _LEAK_FRAME:
            started = self._leak_started_at or time.time()
            elapsed_min = (time.time() - started) / 60.0
            mem = cfg["mem_gb"] * 0.60 + elapsed_min * _LEAK_GB_PER_MIN

        if scenario == "lpar_down" and name == "lpar-web-01":
            state = "Not Activated"
            cpu  = 0.0
            mem  = 0.0

        return LparMetrics(
            name=name,
            frame=frame,
            entitled_cores=cfg["entitled"],
            virtual_processors=cfg["vproc"],
            cpu_utilisation=min(cpu, 1.0),
            memory_used_gb=round(min(mem, cfg["mem_gb"]), 2),
            memory_total_gb=cfg["mem_gb"],
            state=state,
        )

    def _build_vios(self, cfg: dict, frame: str) -> ViosMetrics:
        latency    = _jitter(3.5)          # ms baseline
        throughput = _jitter(850.0, 0.10)  # Mbps baseline
        state = "Running"

        if self._scenario == "vios_disk_latency" and cfg["name"].startswith("vios-01"):
            latency = _jitter(180.0, 0.05)

        return ViosMetrics(
            name=cfg["name"],
            frame=frame,
            disk_latency_ms=round(latency, 2),
            net_throughput_mbps=round(throughput, 2),
            state=state,
        )
