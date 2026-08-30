# Docker Deployment Guide

This is the canonical deployment guide for the Nuki Smart Lock Notification
System (single-container layout, updated August 2026).

## Architecture

Everything runs in **one container** started by one Compose service:

| Process | Role |
| --- | --- |
| `scripts/nuki_monitor.py` | Polls the Nuki Web API, filters events, sends email/Telegram notifications |
| `gunicorn` (Flask `web.app:app`) | Web dashboard on port 5000 |

The entrypoint (`docker-entrypoint.sh`) performs permission checks, bootstraps
the configuration files, then supervises both processes. If either process
exits, the container stops and Docker restarts it (`restart: unless-stopped`).
`init: true` reaps zombie processes.

### Files

- `compose.yaml` — the Compose service (no deprecated `version:` key)
- `Dockerfile` — Python 3.13 slim base, non-root user, healthcheck
- `docker-entrypoint.sh` — bootstrap + supervision
- `.dockerignore` — keeps secrets and local state out of the build context

## Prerequisites

- Docker Engine + Compose plugin v2.24 or newer (`docker compose version`)
- A Nuki Web API token (https://web.nuki.io/ → Account → API)
- The host UID/GID for the runtime user is **999** (see Permissions below)

## Quick Start

```bash
git clone https://github.com/davedavedavenm/nuki-smart-lock-notification.git
cd nuki-smart-lock-notification
cp .env.example .env
# Edit .env — set SECRET_KEY (python3 -c "import secrets; print(secrets.token_hex(32))")
docker compose up -d --build
```

Open `http://<host-ip>:5000/`. First run walks you through the Setup Wizard:

1. **Admin account** — choose your own username and password (no defaults exist)
2. **Nuki API token** — entered and validated live against the Nuki Web API
3. **Telegram** (optional) — bot token + chat ID, bot token validated
4. **Email** (optional) — SMTP settings
5. **Save** — credentials are written to `config/credentials.ini` (chmod 600, owned by the container user) and you land on the login page

The monitor loop picks up the new token automatically; no restart needed.

## Volumes (bind mounts)

| Host path | Container path | Contents |
| --- | --- | --- |
| `./config` | `/app/config` | `config.ini`, `credentials.ini`, `users.json`, `temp_codes.json` |
| `./data` | `/app/data` | Activity history |
| `./logs` | `/app/logs` | Monitor and web logs |
| `./flask_session` | `/app/flask_session` | Server-side web sessions |

All persistent state lives on the host — you can `docker compose down`, pull
updates and `up -d` again without losing anything.

## Permissions

The container runs as the non-root user `nuki` (UID/GID **999**). The mounted
host directories must be writable by that UID:

```bash
mkdir -p config logs data flask_session
sudo chown -R 999:999 config logs data flask_session
```

The entrypoint fails fast with an actionable message if permissions are wrong,
rather than crash-looping.

## Environment Variables

All `NUKI_*` variables from [.env.example](.env.example) are supported and take
priority over `config/config.ini` / `config/credentials.ini` values.

Key variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | *(none — required)* | Flask session signing key. Without it an ephemeral key is generated and sessions don't survive restarts |
| `NUKI_WEB_PORT` | `5000` | Host port for the dashboard |
| `TZ` | `Europe/London` | Container timezone |
| `GUNICORN_WORKERS` | `2` | Web worker count |
| `NUKI_POLLING_INTERVAL` | `60` | Seconds between Nuki API polls |
| `NUKI_NOTIFICATION_TYPE` | `both` | `both`, `telegram`, `email`, or `none` |
| `WEB_HTTPS` | `false` | Set `true` when behind an HTTPS reverse proxy — enables secure session cookies and passkey logins |
| `PROXY_FIX` | `false` | Set `true` when behind a TLS-terminating reverse proxy (Pangolin, Nginx, Caddy) so the app trusts `X-Forwarded-*` headers |
| `DEBUG` | `false` | Debug mode |

## Operations

### Logs

```bash
docker logs -f nuki              # stdout/stderr (rotated: 3 x 10 MB)
tail -f logs/nuki_monitor.log    # monitor log file
tail -f logs/nuki_web.log        # web log file
```

### Health

```bash
docker compose ps                # health status
curl http://localhost:5000/health
```

The healthcheck (every 60s) hits `/health` inside the container.

### Updating

```bash
git pull
docker compose up -d --build
```

### Restarting

```bash
docker compose restart
```

### Entering the container

```bash
docker exec -it nuki bash
```

### Backups

**In-app (recommended):** as an admin, go to **Admin → Backup & Restore**.
Export downloads a JSON bundle of settings, users, temporary codes and — if
you tick *include secrets* — credentials. Restore accepts the same file with
per-section selection and automatically keeps timestamped `.backup-*` copies
of any file it replaces. Secret exports are sensitive: store them encrypted.

**Manual (file-level):** stop writes, then copy the state directories:

```bash
docker compose stop
tar czf nuki-backup-$(date +%F).tar.gz config data
docker compose start
```

`credentials.ini` in the backup contains live secrets — store the archive
securely.

### Rotating the Nuki API token

Either use the web UI (Configuration) or:

```bash
docker exec -it nuki python scripts/token_manager.py
docker compose restart
```

## Security Notes

- The image never bakes in secrets; `.env`, `config/credentials.ini`, logs,
  sessions and data are excluded from the build context via `.dockerignore`
- Compose sets **no default `SECRET_KEY`** — a fixed default would let anyone
  forge session cookies, so it is intentionally required
- The container runs as non-root; only port 5000 is published (bind it to
  `127.0.0.1:5000:5000` in `compose.yaml` if you front it with a reverse proxy)
- **Passkeys (WebAuthn)**: users can register passkeys on their profile page
  and sign in with fingerprint/face/device PIN instead of a password. Browsers
  only allow this over HTTPS (or localhost) — set `WEB_HTTPS=true` in `.env`
  when running behind an HTTPS reverse proxy so secure session cookies are set
- See [SECURITY.md](SECURITY.md) for the full security policy
