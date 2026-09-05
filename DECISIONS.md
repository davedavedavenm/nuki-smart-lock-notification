# Decisions — Nuki Smart Lock Notification

Settled, closed questions for this repo. Check here before proposing to
change, redo, or re-open something; update this file in the same session a
decision is settled or reversed.

Status values: **Active** · **Superseded** · **Historical**.

---

## Standalone by design — Active

This repo is deliberately independent, with its own Telegram integration
rather than routing through the shared notification stack. See
`infra/docs/protocols/repo-map.md` — independence here is a stated feature,
not a gap to "fix" by integrating it into n8n/universalcron.

## Live lock safety — Active

Never perform live lock-affecting actions unless the user explicitly asks.
Prefer tests and local mocks before touching live locks or notification
channels.

## Single-container deployment — Active (2026-08)

One Docker container runs both the monitor loop and the web dashboard
(gunicorn), supervised by `docker-entrypoint.sh` and defined in a single
`compose.yaml` service. This replaces the previous two-container
(`nuki-monitor` + `nuki-web`) layout and the native systemd/Raspberry Pi
install path. If either process dies the container exits and Docker restarts
it. Do not reintroduce multi-container or systemd deployment docs.

## No baked-in secrets — Active (2026-08)

`SECRET_KEY` has no fixed default in compose/Dockerfile (the old hardcoded
`nuki-smart-lock-dashboard-fixed-key` was removed). Without `SECRET_KEY` in
`.env` the entrypoint generates an ephemeral key and warns. `.env`,
`credentials.ini`, logs, sessions and data are excluded from the build context
via `.dockerignore`, and CI runs `sanitize_check.py` as a gate.

## No default credentials — Active (2026-08)

The old auto-created `admin`/`nukiadmin` account was removed (including the
`web/app.py` `__main__` fallback and `reset_users.py` defaults). A fresh
install has zero user accounts; the Setup Wizard walks the user through
creating their own admin account. Do not reintroduce default users, placeholder
tokens in seeded config files, or any bypass of the wizard gate.

## Staged setup wizard, nothing lost — Active (2026-08)

`/api/setup` is staged (`admin` → `nuki` → `telegram` → `email` → `done`):
each stage validates and saves immediately, so a mistake never discards
earlier input, and an in-progress setup resumes from the creating session.
The admin stage logs the user in; Telegram and Email stages are optional and
explicitly skippable. The wizard closes to third parties the moment an admin
account exists. Do not regress to single-shot save-at-the-end validation.

## API tokens, scoped — Active (2026-08)

Nuki connection uses Nuki Web API tokens, not OAuth2: Nuki's OAuth2 code flow
requires a client_secret only issued after an Advanced API Integration
approval (aimed at software suppliers), and its refresh tokens can be
invalidated by the user logging in elsewhere — both impractical for a
self-hosted monitor. Instead the wizard guides users to create a scoped,
read-only API token (least privilege). OAuth2 can be revisited only if Nuki
opens client secrets to self-hosters.

## Dark mode by default — Active (2026-08)

The web UI defaults to the dark theme for new sessions and fresh installs
(`DEFAULT_THEME=dark`); light mode remains user-selectable via the toggle.

## Passkeys as an optional login method — Active (2026-08)

WebAuthn passkeys (python-fido2) are supported alongside passwords:
usernameless login from the login page, registration/management from the
profile page. Passkeys are never mandatory — passwords remain the baseline so
plain-HTTP LAN access always works. Browsers only offer WebAuthn in secure
contexts (HTTPS or localhost), so the UI hides passkey options when insecure;
set `WEB_HTTPS=true` behind a reverse proxy. Do not ship other login
mechanisms without user sign-off.

## Webhook as wake signal, polling as the source of truth — Active (2026-09)

Nuki notification hooks (`POST /webhook/nuki/<secret>`) only *wake* the
monitor to poll immediately; event extraction, dedup and notification always
go through the existing polling path. This keeps one code path for events
(no double-notify risk, no separate webhook payload parser) and makes the
webhook a pure latency optimisation — polling remains the fallback when the
tunnel or hook is down. The URL-path secret is the only credential because
Nuki's hooks cannot send custom headers; the endpoint is POST-only,
rate-limited, audited, and meant to live on a dedicated hostname without
proxy SSO. Do not switch to processing webhook payloads directly.

## System alerts bypass the "none" channel — Active (2026-09)

`notification_type = none` disables *event* notifications, but self-monitoring
alerts (repeated poll failures, 401 auth failure, recovery, failed sign-ins)
are still delivered via Telegram if configured, else email. Their purpose is
to report that the notification system itself is broken, so letting the same
switch silence them would defeat it. Alerts are one-shot per failure episode
and rate-limited; do not make them per-event chatty.

## Quiet hours defer to digest, never drop — Active (2026-09)

Events inside the quiet window are queued and flushed as one digest when the
window ends (windows may span midnight). Nothing is discarded. Digest sends
are also suppressed during quiet hours and flushed on exit.
