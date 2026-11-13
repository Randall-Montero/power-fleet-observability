"""Unit tests for the SimulatedSource."""
import os
import sys

# Allow importing exporter modules without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sources.simulated import SimulatedSource
from sources.base import FrameMetrics, LparMetrics, ViosMetrics


@pytest.fixture(autouse=True)
def clear_scenario(monkeypatch):
    monkeypatch.delenv("SCENARIO", raising=False)


# ── basic structure ────────────────────────────────────────────────────────────

def test_collect_returns_two_frames():
    src = SimulatedSource()
    frames = src.collect()
    assert len(frames) == 2


def test_each_frame_has_five_lpars():
    src = SimulatedSource()
    for frame in src.collect():
        assert len(frame.lpars) == 5, f"{frame.name} has {len(frame.lpars)} LPARs"


def test_each_frame_has_two_vios():
    src = SimulatedSource()
    for frame in src.collect():
        assert len(frame.vios_list) == 2


def test_lpar_cpu_within_bounds():
    src = SimulatedSource()
    for frame in src.collect():
        for lpar in frame.lpars:
            assert 0.0 <= lpar.cpu_utilisation <= 1.0, (
                f"{lpar.name} cpu={lpar.cpu_utilisation}"
            )


def test_lpar_memory_used_not_exceed_total():
    src = SimulatedSource()
    for frame in src.collect():
        for lpar in frame.lpars:
            assert lpar.memory_used_gb <= lpar.memory_total_gb


def test_is_healthy_without_scenario():
    src = SimulatedSource()
    assert src.is_healthy() is True


# ── scenario: cpu_saturation ──────────────────────────────────────────────────

def test_scenario_cpu_saturation(monkeypatch):
    monkeypatch.setenv("SCENARIO", "cpu_saturation")
    src = SimulatedSource()
    frames = src.collect()
    frame01 = next(f for f in frames if f.name == "frame01")
    db2 = next(l for l in frame01.lpars if l.name == "lpar-db2-01")
    assert db2.cpu_utilisation >= 0.95


# ── scenario: memory_leak ─────────────────────────────────────────────────────

def _app01_mem(frames):
    frame01 = next(f for f in frames if f.name == "frame01")
    return next(l for l in frame01.lpars if l.name == "lpar-app-01").memory_used_gb


def test_scenario_memory_leak_grows_after_activation(monkeypatch):
    monkeypatch.setenv("SCENARIO", "memory_leak")
    src = SimulatedSource()
    first = _app01_mem(src.collect())
    # pretend the scenario has been active for 4 minutes
    src._leak_started_at -= 240
    later = _app01_mem(src.collect())
    assert later > first + 10
    assert later / 64.0 > 0.90


def test_memory_leak_does_not_start_before_activation(monkeypatch):
    src = SimulatedSource()
    src.collect()                       # baseline collections, no scenario
    monkeypatch.setenv("SCENARIO", "memory_leak")
    mem = _app01_mem(src.collect())     # first tick with the scenario
    assert mem / 64.0 < 0.70


def test_memory_leak_resets_when_cleared(monkeypatch):
    monkeypatch.setenv("SCENARIO", "memory_leak")
    src = SimulatedSource()
    src.collect()
    src._leak_started_at -= 240
    monkeypatch.delenv("SCENARIO")
    src.collect()
    assert src._leak_started_at is None


# ── scenario: lpar_down ───────────────────────────────────────────────────────

def test_scenario_lpar_down(monkeypatch):
    monkeypatch.setenv("SCENARIO", "lpar_down")
    src = SimulatedSource()
    frames = src.collect()
    frame01 = next(f for f in frames if f.name == "frame01")
    web = next(l for l in frame01.lpars if l.name == "lpar-web-01")
    assert web.state == "Not Activated"
    assert web.cpu_utilisation == 0.0


# ── scenario: frame_overcommit ────────────────────────────────────────────────

def test_scenario_frame_overcommit(monkeypatch):
    monkeypatch.setenv("SCENARIO", "frame_overcommit")
    src = SimulatedSource()
    frames = src.collect()
    frame01 = next(f for f in frames if f.name == "frame01")
    assert frame01.allocated_cores > frame01.total_cores


# ── scenario: vios_disk_latency ───────────────────────────────────────────────

def test_scenario_vios_disk_latency(monkeypatch):
    monkeypatch.setenv("SCENARIO", "vios_disk_latency")
    src = SimulatedSource()
    frames = src.collect()
    frame01 = next(f for f in frames if f.name == "frame01")
    for vios in frame01.vios_list:
        assert vios.disk_latency_ms > 50, (
            f"{vios.name} latency={vios.disk_latency_ms} expected > 50 ms"
        )


# ── scenario: hmc_unreachable ─────────────────────────────────────────────────

def test_scenario_hmc_unreachable(monkeypatch):
    monkeypatch.setenv("SCENARIO", "hmc_unreachable")
    src = SimulatedSource()
    assert src.is_healthy() is False


# ── HMC skeleton ─────────────────────────────────────────────────────────────

def test_hmc_source_collect_returns_empty():
    from sources.hmc import HmcSource
    src = HmcSource()
    assert src.collect() == []


def test_hmc_source_is_healthy_returns_false():
    from sources.hmc import HmcSource
    src = HmcSource()
    assert src.is_healthy() is False
