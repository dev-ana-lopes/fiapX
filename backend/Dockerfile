FROM python:3.14-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system -e .
COPY apps ./apps
COPY packages ./packages
COPY migrations ./migrations
COPY alembic.ini ./
ENV PYTHONPATH=/app/apps/api/src:/app/apps/video_worker/src:/app/apps/notification_worker/src:/app/packages/shared
CMD ["uvicorn", "fiapx_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
