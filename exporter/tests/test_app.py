"""Tests for the exporter's gauge publishing (app.py)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from prometheus_client import REGISTRY

import app
from sources.simulated import SimulatedSource


@pytest.fixture(autouse=True)
def clear_scenario(monkeypatch):
    monkeypatch.delenv("SCENARIO", raising=False)


def _lpar_state(lpar):
    return REGISTRY.get_sample_value(
        "power_lpar_state", {"frame": "frame01", "lpar": lpar}
    )


def test_lpar_state_is_single_series_without_state_label():
    app.collect_and_update(SimulatedSource())
    assert _lpar_state("lpar-web-01") == 1.0


def test_lpar_down_flips_the_same_series_to_zero(monkeypatch):
    src = SimulatedSource()
    app.collect_and_update(src)
    assert _lpar_state("lpar-web-01") == 1.0

    monkeypatch.setenv("SCENARIO", "lpar_down")
    app.collect_and_update(src)
    # the series that LparDown evaluates (power_lpar_state == 0) must now exist
    assert _lpar_state("lpar-web-01") == 0.0


def test_lpar_recovers_after_clear(monkeypatch):
    src = SimulatedSource()
    monkeypatch.setenv("SCENARIO", "lpar_down")
    app.collect_and_update(src)
    monkeypatch.delenv("SCENARIO")
    app.collect_and_update(src)
    assert _lpar_state("lpar-web-01") == 1.0
