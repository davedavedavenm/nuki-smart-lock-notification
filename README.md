# Nuki Smart Lock Notification System

A self-hosted notification system for the Nuki Smart Lock, using the Nuki Web API. It monitors lock activity and sends customizable notifications via email and/or Telegram, with a built-in web dashboard.

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- 🔒 **Secure Monitoring**: Connect to the Nuki Web API with proper authentication
- 🔔 **Instant Notifications**: Email and/or Telegram alerts when the lock is used
- 👤 **User Identification**: Track which user operated the lock
- 🌐 **Web Dashboard**: Monitor activity, manage users and configuration
- 🕒 **Activity Logging**: Detailed history of lock activity
- 🔄 **Digest Mode**: Summaries of activities instead of individual notifications
- 🔍 **Smart Filtering**: Filter by user, action type, or trigger type
- 🌙 **Dark Mode**: Toggle between light and dark themes
- 👥 **User Management**: Multiple users with admin/agent roles
- 🔑 **Agent Access**: Let agents create temporary access codes
- 🫆 **Passkey Sign-in**: Optional WebAuthn login (fingerprint/face/PIN) alongside passwords
- 🐳 **Single-Container Docker Deployment**: One `docker compose up -d` and you're running

## Requirements

- Any host with Docker and Docker Compose v2.24+ (Raspberry Pi 4, NAS, VPS, desktop — anything Docker runs on)
- A Nuki Smart Lock paired with a [Nuki Web](https://web.nuki.io/) account and API token

## Quick Start (Docker)

1. Clone the repository and configure:

   ```bash
   git clone https://github.com/davedavedavenm/nuki-smart-lock-notification.git
   cd nuki-smart-lock-notification
   cp .env.example .env
   ```

2. Generate a secret key and put it in `.env`:

   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   # paste the output into SECRET_KEY= in .env
   ```

3. Start the stack:

   ```bash
   docker compose up -d --build
   ```

4. Open `http://<host-ip>:5000`. On first run you are walked through the **Setup Wizard**:
   1. Create your own admin account (there are **no default logins**)
   2. Enter your Nuki API token — validated against the Nuki Web API as you go
   3. Optionally add Telegram and email notification credentials
   4. Save — everything is written to `config/credentials.ini` and `config/config.ini` with permissions restricted to the app user, and you're taken to the login page

That's it — one container runs both the monitor loop and the web dashboard. Full deployment details, permissions, backups and upgrades are in [DOCKER_GUIDE.md](DOCKER_GUIDE.md).

## Architecture

```
┌────────────── single container (nuki) ──────────────┐
│  monitor loop (polls Nuki API → email/Telegram)     │
│  web dashboard (gunicorn :5000 → Flask)             │
├────────────────── bind-mounted volumes ─────────────┤
│  ./config  (config.ini, credentials.ini, users)     │
│  ./data    (activity history)                       │
│  ./logs    (monitor + web logs)                     │
│  ./flask_session  (server-side sessions)            │
└─────────────────────────────────────────────────────┘
```

## Configuration

Configuration lives in two layers:

1. **Environment variables** (`.env`) — see [.env.example](.env.example) for every supported `NUKI_*` variable. Environment values take priority over the config files.
2. **Config files** (`config/config.ini`, `config/credentials.ini`) — edited by the web UI, or manually from the examples in [`config/`](config/). `credentials.ini` holds your Nuki API token, Telegram bot token and email credentials and is git-ignored.

### Getting a Nuki API Token

1. Log in to the [Nuki Web Dashboard](https://web.nuki.io/)
2. Go to **Account → API** and generate a new API token
3. Enter it in the Setup Wizard (or `config/credentials.ini` under `[Nuki]`)

### Setting up Telegram Notifications

1. Create a bot with [@BotFather](https://t.me/botfather) and copy the bot token into `credentials.ini`
2. Get your chat ID:
   ```bash
   docker exec -it nuki python scripts/get_telegram_chat_id.py
   ```
3. Add the chat ID to `config/config.ini` under `[Telegram]`

## Web Interface

- **Dashboard** — current lock status and recent activity
- **Activity** — complete activity history
- **Status** — status of all your locks
- **Temporary Codes** — create/manage temporary access codes (admin and agent roles)
- **Configuration / Users / Notifications** — admin-only management pages

Access the dashboard at `http://<host-ip>:5000`. Roles: **admin** (full access) and **agent** (temporary code management only — see [docs/management_agency.md](docs/management_agency.md)).

## Security

- Runs as a non-root container user (UID/GID 999)
- No baked-in secrets: `SECRET_KEY` must come from your `.env` (or an ephemeral key is generated per start)
- **No default credentials**: the first admin account is created by you in the Setup Wizard
- `config/credentials.ini`, `.env`, logs, sessions and activity data are git-ignored and excluded from the Docker build context
- Passwords hashed (PBKDF2 via Werkzeug); role-based access control
- CI runs an automated secrets scan (`sanitize_check.py`) on every push

See [SECURITY.md](SECURITY.md) for the full policy and reporting instructions.

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues (permissions, 401 Unauthorized, health checks, logs).

Quick health check:

```bash
curl http://<host-ip>:5000/health
docker logs nuki
```

## Repository Layout

```
├── scripts/               # Monitor loop, Nuki API client, config, utilities
│   └── nuki/              # Core package (api, config, notification, utils)
├── security/              # Security monitoring and alerting module
├── web/                   # Flask dashboard (app, models, templates, static)
├── config/                # Config examples (real files are git-ignored)
├── tests/                 # pytest suite
├── docs/                  # Additional documentation
├── compose.yaml           # Single-service Docker Compose definition
├── Dockerfile             # Single-container image (monitor + web)
└── docker-entrypoint.sh   # Permission checks + process supervision
```

## Documentation

| Document | What it covers |
| --- | --- |
| [DOCKER_GUIDE.md](DOCKER_GUIDE.md) | Deploying, configuring, operating, backing up (start here) |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Permissions, 401s, passkeys, sessions, resets |
| [docs/configuration.md](docs/configuration.md) | Every config file and setting explained |
| [docs/management_agency.md](docs/management_agency.md) | Agent accounts and temporary access codes |
| [SECURITY.md](SECURITY.md) | Security model and how to report vulnerabilities |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup and running the tests |
| [DECISIONS.md](DECISIONS.md) | Settled design decisions and their reasoning |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: `pip install -r requirements-dev.txt`, then `pytest`. CI runs the tests plus a secrets scan on Python 3.11–3.13.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [Nuki](https://nuki.io/) for the Smart Lock and Web API
- The Python and Flask communities
- All contributors to this project
