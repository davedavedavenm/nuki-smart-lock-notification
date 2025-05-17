FROM python:3.9-slim-bullseye

WORKDIR /app

# Install dependencies and system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt
RUN pip install --no-cache-dir psutil gunicorn

# Copy application code
COPY app /app/app
COPY config /app/config
COPY docker/web/entrypoint.sh /app/
COPY docker/web/fix-template.sh /app/

# Create directories with proper permissions
RUN mkdir -p /app/logs /app/data \
    && chmod -R 777 /app/logs /app/data \
    && chmod -R 777 /app/config

# Make the entrypoint scripts executable
RUN chmod +x /app/entrypoint.sh
RUN chmod +x /app/fix-template.sh

# Set environment variables
ENV CONFIG_DIR=/app/config
ENV LOGS_DIR=/app/logs
ENV FLASK_APP=app.web.app
ENV PYTHONUNBUFFERED=1

# Run as non-root user for security
RUN groupadd -r nuki && useradd -r -g nuki nuki \
    && chown -R nuki:nuki /app

USER nuki

# Expose the web port
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the Flask application with fixes
ENTRYPOINT ["/app/fix-template.sh", "/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app.web.app:app"]
