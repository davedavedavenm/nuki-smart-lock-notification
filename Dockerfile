# Single-container image: Nuki monitor loop + web dashboard (gunicorn).
# Updated August 2026: Python 3.13 / Debian slim, non-root, multi-process entrypoint.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first for layer caching
COPY requirements-web.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt

# Create non-root user
RUN groupadd --system nuki && useradd --system --gid nuki nuki

# Copy application code
COPY --chown=nuki:nuki scripts /app/scripts
COPY --chown=nuki:nuki security /app/security
COPY --chown=nuki:nuki web /app/web
COPY --chown=nuki:nuki config /app/config
COPY --chown=nuki:nuki docker-entrypoint.sh /app/docker-entrypoint.sh

# Prepare runtime directories
RUN mkdir -p /app/logs /app/data /app/flask_session \
    && chown -R nuki:nuki /app \
    && chmod +x /app/docker-entrypoint.sh

USER nuki

ENV CONFIG_DIR=/app/config \
    DATA_DIR=/app/data \
    LOGS_DIR=/app/logs \
    SESSION_FILE_DIR=/app/flask_session \
    ALLOW_MISSING_TOKEN=true

EXPOSE 5000

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health',timeout=5).status==200 else 1)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
