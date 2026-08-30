#!/usr/bin/env bash
# Single-container entrypoint: permission checks, config bootstrap,
# then run the monitor loop (background) + gunicorn web UI (foreground).
set -e

CONFIG_DIR="${CONFIG_DIR:-/app/config}"
LOGS_DIR="${LOGS_DIR:-/app/logs}"

echo "[entrypoint] Starting Nuki Smart Lock Notification (single container)"

# --- Permission sanity checks (fail fast with actionable messages) ---
if [ -f "$CONFIG_DIR/credentials.ini" ] && ! [ -r "$CONFIG_DIR/credentials.ini" ]; then
    echo "[entrypoint] ERROR: cannot read $CONFIG_DIR/credentials.ini"
    echo "[entrypoint] Fix on the host: chmod 644 config/credentials.ini (and ensure UID/GID match)"
    exit 1
fi
if ! [ -w "$LOGS_DIR" ]; then
    echo "[entrypoint] ERROR: $LOGS_DIR is not writable by the container user"
    echo "[entrypoint] Fix on the host: chown -R 999:999 logs data config flask_session"
    exit 1
fi
if ! [ -w "$CONFIG_DIR" ]; then
    echo "[entrypoint] ERROR: $CONFIG_DIR is not writable by the container user"
    echo "[entrypoint] Fix on the host: chown -R 999:999 config"
    exit 1
fi

# --- Ensure configuration files exist (creates examples if missing) ---
python /app/scripts/ensure_config.py
echo "[entrypoint] Configuration verified"

# --- SECRET_KEY: never ship a fixed default ---
if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
    export SECRET_KEY
    echo "[entrypoint] WARNING: SECRET_KEY not set; generated a random ephemeral key."
    echo "[entrypoint]          Web sessions will not survive container restarts."
    echo "[entrypoint]          Set SECRET_KEY in .env for persistent sessions."
fi

# --- Start monitor loop in background ---
python /app/scripts/nuki_monitor.py &
MONITOR_PID=$!

shutdown() {
    echo "[entrypoint] Shutting down..."
    kill -TERM "$MONITOR_PID" "${WEB_PID:-}" 2>/dev/null || true
    wait 2>/dev/null || true
    exit 0
}
trap shutdown TERM INT

# --- Start web UI in foreground ---
GUNICORN_WORKERS="${GUNICORN_WORKERS:-2}"
gunicorn --bind 0.0.0.0:5000 \
         --workers "$GUNICORN_WORKERS" \
         --timeout 60 \
         --access-logfile - \
         --error-logfile - \
         web.app:app &
WEB_PID=$!

echo "[entrypoint] Monitor (PID $MONITOR_PID) and web UI (PID $WEB_PID) running"

# If either process dies, tear down both so the container restarts cleanly.
wait -n "$MONITOR_PID" "$WEB_PID"
STATUS=$?
echo "[entrypoint] A child process exited (status $STATUS); stopping container"
shutdown
