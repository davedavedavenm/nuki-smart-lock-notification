# AGENTS.md — Nuki Smart Lock Notification

Notification and dashboard system for Nuki Smart Lock events, with email/Telegram notification paths and optional Docker deployment.

## Scope

- Python app, web UI, Docker files, install scripts, tests, and docs for Nuki monitoring.
- Do not commit `.env`, Nuki API tokens, notification credentials, logs, or local Flask/session data.

## MCPProxy / Tool Surfaces

- Use the MCPProxy instance local to where the agent is running. Windows normally uses `http://127.0.0.1:8080/mcp`; `khpi5` uses `http://127.0.0.1:9092` for work started on that host.
- Discover tools before calling them and use exact `server:tool` names.
- Use Telegram/email MCP surfaces only for explicit delivery proof tasks, and never expose recipient details.
- Nango surfaces are not primary unless the task explicitly involves email/calendar/Notion/GitHub proof. Pick the correct account before any write.
- Appwrite is not part of this repo.

## Core Rules

1. Prefer tests and local mocks before touching live locks or notification channels.
2. Never perform live lock-affecting actions unless the user explicitly asks.
3. Keep security-sensitive logs and tokens out of git.
4. Stage only intentional files; never `git add -A`.

