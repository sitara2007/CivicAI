# 1. Base Stage
FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# 2. Builder Stage
FROM base AS worker
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
# Copy source code
COPY . .

# Pip upgrade aur PyTorch install
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir '.[rag]'

# 3. Runtime Stage
FROM base AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /usr/sbin/nologin appuser

# Copy virtual environment aur app folder from builder
COPY --from=worker /opt/venv /opt/venv
COPY --from=worker /app /app

USER appuser
EXPOSE 8000
ENTRYPOINT ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
