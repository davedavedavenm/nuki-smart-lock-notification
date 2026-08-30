# Troubleshooting

Common issues with the single-container Docker deployment. For general
deployment steps see [DOCKER_GUIDE.md](DOCKER_GUIDE.md).

## Container fails to start: permission errors

The container runs as user `nuki` (UID/GID 999). If the entrypoint reports:

```
ERROR: /app/config is not writable by the container user
```

Fix ownership on the host:

```bash
mkdir -p config logs data flask_session
sudo chown -R 999:999 config logs data flask_session
```

Then `docker compose up -d`.

## API Authentication Failed (401 Unauthorized)

- Your Nuki API token has expired or been revoked
- Rotate it in the web UI (Configuration), or:
  ```bash
  docker exec -it nuki python scripts/token_manager.py
  docker compose restart
  ```

## No notifications despite correct configuration

- Check the monitor log: `tail -f logs/nuki_monitor.log`
- Verify filters in `config/config.ini` (`[Filter]` section) are not excluding
  your events
- Verify `[Telegram]` / `[Email]` settings; test the API token with:
  ```bash
  docker exec -it nuki python scripts/verify_token.py
  ```

## Web interface not reachable

- Container running and healthy?
  ```bash
  docker compose ps
  curl http://localhost:5000/health
  ```
- Wrong port? `NUKI_WEB_PORT` in `.env` maps the host port (default 5000)
- Check web logs: `docker logs nuki` and `logs/nuki_web.log`

## Web sessions lost on every restart

You did not set `SECRET_KEY` in `.env`, so an ephemeral key is generated each
start. Add a persistent key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# paste into SECRET_KEY= in .env, then:
docker compose up -d
```

## Passkey option not showing / not working

Passkeys (WebAuthn) only work in a **secure context**:

- `http://localhost:5000` — works
- `http://<lan-ip>:5000` — browsers block WebAuthn here; the passkey option is hidden by design
- Behind an HTTPS reverse proxy — set `WEB_HTTPS=true` in `.env` so secure
  cookies are used, and the passkey option appears

Password login always remains available regardless.

## Monitor or web process crashed

The entrypoint stops the whole container if either process dies, so Docker
restarts everything cleanly. Investigate with:

```bash
docker logs nuki
```

`docker inspect nuki --format '{{json .State.Health}}'` shows recent
healthcheck output.

## Resetting everything (start fresh)

```bash
docker compose down
rm -rf config/* data/* logs/* flask_session/*
docker compose up -d --build
```

⚠️ This deletes all users, configuration and history.
