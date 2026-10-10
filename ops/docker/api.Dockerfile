FROM ghcr.io/astral-sh/uv:0.12.17 AS uv
FROM python:3.13-slim
COPY --from=uv /uv /uvx /usr/local/bin/
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/services \
    UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --extra api --extra research --extra product
COPY services/ ./services/
COPY db/ ./db/
COPY research/events/2026-09-17-spk-liquidations/price_detectors/detectors.py ./research/events/2026-09-17-spk-liquidations/price_detectors/detectors.py
RUN groupadd --gid 10001 p50k && useradd --uid 10001 --gid p50k --no-create-home p50k
USER p50k
CMD ["python", "-m", "uvicorn", "p50k.product.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
