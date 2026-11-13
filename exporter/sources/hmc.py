"""HMC data source skeleton — for use in a real IBM Power lab.

This source is intentionally left as a documented skeleton.
To activate it set:  POWER_SOURCE=hmc

Environment variables expected:
  HMC_HOST      – hostname or IP of the Hardware Management Console
  HMC_USER      – HMC user with monitoring permissions
  HMC_PASSWORD  – HMC password (mount from a Kubernetes Secret)

Required Python library (not included in requirements.txt):
  pyhmcrest (https://github.com/POWERVM/pyHMCREST)

Typical HMC REST flow:
  1. POST /rest/api/web/Logon  → session token
  2. GET  /rest/api/uom/ManagedSystem  → list of frames
  3. GET  /rest/api/uom/ManagedSystem/{uuid}/LogicalPartition  → LPARs
  4. GET  /rest/api/uom/ManagedSystem/{uuid}/VirtualIOServer  → VIOS
  5. Map HMC JSON fields to FrameMetrics / LparMetrics / ViosMetrics
  6. POST /rest/api/web/Logon  (DELETE) → log out
"""
from __future__ import annotations

import logging
import os
from typing import List

from .base import FrameMetrics, PowerSource

log = logging.getLogger(__name__)


class HmcSource(PowerSource):
    """IBM Hardware Management Console data source (skeleton)."""

    def __init__(self) -> None:
        self._host     = os.environ.get("HMC_HOST", "")
        self._user     = os.environ.get("HMC_USER", "")
        self._password = os.environ.get("HMC_PASSWORD", "")
        self._session  = None   # pyhmcrest session handle

    # ── public API ────────────────────────────────────────────────────────────

    def collect(self) -> List[FrameMetrics]:
        """Collect metrics from the HMC REST API.

        TODO (lab exercise):
          1. Import pyhmcrest and open a session.
          2. Iterate managed systems and fetch LPAR / VIOS data.
          3. Translate to FrameMetrics / LparMetrics / ViosMetrics.
        """
        log.warning(
            "HmcSource.collect() is a skeleton — returning empty list. "
            "Implement using pyhmcrest against HMC_HOST=%s",
            self._host,
        )
        return []

    def is_healthy(self) -> bool:
        """Ping the HMC to verify connectivity.

        TODO (lab exercise):
          Return False when the HMC is unreachable or credentials are invalid.
        """
        log.warning("HmcSource.is_healthy() is a skeleton — returning False.")
        return False
