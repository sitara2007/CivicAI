# 1. Base Stage
FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# 2. Builder Stage
FROM base AS worker
# Use shell directly to avoid issues
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
COPY pyproject.toml ./
# Pip upgrade aur PyTorch install ko alag step mein rakho
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir '.[rag]'

# 3. Runtime Stage
FROM base AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /usr/sbin/nologin appuser

COPY --from=worker /opt/venv /opt/venv
COPY app ./app
USER appuser
EXPOSE 8000
ENTRYPOINT ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
