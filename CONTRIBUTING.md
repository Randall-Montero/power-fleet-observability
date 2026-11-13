# Contributing to power-fleet-observability

Thank you for your interest in contributing! This guide explains how to get involved.

---

## Getting Started

1. **Fork** the repository and clone your fork.
2. Create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```
3. Make your changes, commit with a clear message, and push to your fork.
4. Open a **Pull Request** against `main`.

---

## Development Setup

```bash
# Install Python dependencies
pip install -r exporter/requirements.txt pytest

# Run the exporter locally
cd exporter
POWER_SOURCE=simulated python app.py

# Run tests
pytest exporter/tests -v
```

---

## Code Style

- Python: follow [PEP 8](https://peps.python.org/pep-0008/). Keep functions small and focused.
- YAML: 2-space indent, one resource per `---` block.
- Shell: `set -euo pipefail` at the top of every script.
- Commit messages: `type(scope): short description` (e.g. `feat(exporter): add memory_leak scenario`).

---

## Adding a New Scenario

1. Add a branch in `SimulatedSource._build_lpar()` or `_build_vios()` in [`exporter/sources/simulated.py`](exporter/sources/simulated.py).
2. Document the scenario in the module docstring.
3. Add it to the `VALID_SCENARIOS` list in [`scripts/inject_scenario.sh`](scripts/inject_scenario.sh).
4. Write a test in [`exporter/tests/test_simulated.py`](exporter/tests/test_simulated.py).
5. Add a matching alert rule in [`monitoring/rules/power-fleet-alerts.yml`](monitoring/rules/power-fleet-alerts.yml).

---

## Adding a New Alert Rule

1. Edit [`monitoring/rules/power-fleet-alerts.yml`](monitoring/rules/power-fleet-alerts.yml).
2. Validate locally:
   ```bash
   promtool check rules monitoring/rules/power-fleet-alerts.yml
   ```
3. Nothing else to edit: `scripts/demo.sh` builds the `prometheus-rules` ConfigMap from that file. Re-run `bash scripts/demo.sh` and Prometheus picks it up.

---

## Pull Request Checklist

- [ ] `pytest exporter/tests` passes with no failures
- [ ] `promtool check rules monitoring/rules/power-fleet-alerts.yml` passes
- [ ] Docker image builds: `docker build -t power-fleet-observability .`
- [ ] New scenarios are documented in README.md
- [ ] No credentials or secrets are committed

---

## Reporting Issues

Open a GitHub Issue with:
- A clear title
- Steps to reproduce
- Expected vs actual behaviour
- Relevant logs or screenshots

---

## License

By contributing you agree that your contributions will be licensed under the [Apache 2.0 License](LICENSE.md).
