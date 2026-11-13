"""Base interface for Power fleet data sources."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class LparMetrics:
    name: str
    frame: str
    entitled_cores: float
    virtual_processors: int
    cpu_utilisation: float   # 0.0 – 1.0
    memory_used_gb: float
    memory_total_gb: float
    state: str               # "Running" | "Not Activated" | "Error"


@dataclass
class ViosMetrics:
    name: str
    frame: str
    disk_latency_ms: float
    net_throughput_mbps: float
    state: str               # "Running" | "Error"


@dataclass
class FrameMetrics:
    name: str
    total_cores: float
    allocated_cores: float
    lpars: List[LparMetrics] = field(default_factory=list)
    vios_list: List[ViosMetrics] = field(default_factory=list)


class PowerSource(ABC):
    """Abstract base class every data source must implement."""

    @abstractmethod
    def collect(self) -> List[FrameMetrics]:
        """Return a snapshot of all frames, LPARs and VIOS."""
        ...

    @abstractmethod
    def is_healthy(self) -> bool:
        """Return False when the source itself is unavailable."""
        ...
