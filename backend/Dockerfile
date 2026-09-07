FROM python:3.14-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv==0.8.14
COPY pyproject.toml uv.lock ./
COPY apps ./apps
COPY packages ./packages
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

FROM python:3.14-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/apps ./apps
COPY --from=builder /app/packages ./packages
COPY --from=builder /app/migrations ./migrations
COPY --from=builder /app/alembic.ini ./
ENV PYTHONPATH=/app/apps/api/src:/app/apps/video_worker/src:/app/apps/notification_worker/src:/app/packages/shared
ENV PATH=/app/.venv/bin:$PATH
USER app
CMD ["uvicorn", "fiapx_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
