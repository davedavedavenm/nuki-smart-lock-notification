FROM python:3.9-slim-bullseye

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app
COPY config /app/config
COPY docker/monitor/entrypoint.sh /app/

# Create directories with proper permissions and set appropriate ownership
RUN mkdir -p /app/logs /app/data /app/flask_session \
    && chmod -R 777 /app/logs /app/data /app/flask_session \
    && chmod -R 777 /app/config \
    && touch /app/logs/nuki_monitor.log /app/logs/health_monitor.log \
    && chmod 666 /app/logs/nuki_monitor.log /app/logs/health_monitor.log

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV CONFIG_DIR=/app/config
ENV LOGS_DIR=/app/logs
ENV PYTHONUNBUFFERED=1

# While we'd prefer to run as a non-root user for security,
# we'll run as root initially to handle permission issues
# This can be changed back to a non-root user once the system is stable
#RUN groupadd -r nuki && useradd -r -g nuki nuki \
#    && chown -R nuki:nuki /app
#USER nuki

# Running as root for now to handle permissions
RUN echo "Running as root to handle filesystem permissions"

# Add healthcheck
HEALTHCHECK --interval=5m --timeout=20s --start-period=30s --retries=3 \
    CMD python /app/app/monitoring/health_monitor.py || exit 1

# Run the monitor script
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "app.monitoring.nuki_monitor"]
