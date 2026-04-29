# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Production ───────────────────────────────────────────────────────
FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy only what's needed from builder
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create user first, then copy files with correct ownership
RUN adduser --disabled-password --gecos '' appuser

COPY --chown=appuser:appuser . .
COPY --chown=appuser:appuser docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]