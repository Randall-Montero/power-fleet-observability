# ── build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /app
COPY exporter/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim
LABEL org.opencontainers.image.title="power-fleet-observability-exporter"
LABEL org.opencontainers.image.description="Prometheus exporter for IBM Power fleet metrics"

WORKDIR /app
COPY --from=builder /install /usr/local
COPY exporter/ .

ENV POWER_SOURCE=simulated \
    SCENARIO="" \
    EXPORTER_PORT=8000 \
    SCRAPE_INTERVAL=15

EXPOSE 8000
USER nobody
ENTRYPOINT ["python", "app.py"]
