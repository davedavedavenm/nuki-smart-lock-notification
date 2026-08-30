# AGENTS.md — Nuki Smart Lock Notification

Notification and dashboard system for Nuki Smart Lock events, with email/Telegram notification paths and optional Docker deployment.

Read [DECISIONS.md](DECISIONS.md) before starting work — settled, closed
questions (standalone-by-design, live lock safety). Check before proposing
to change or redo something.

## Scope

- Python app, web UI, Docker files, install scripts, tests, and docs for Nuki monitoring.
- Do not commit `.env`, Nuki API tokens, notification credentials, logs, or local Flask/session data.

## MCPProxy / Tool Surfaces

- Use the MCPProxy instance local to where the agent is running. Windows normally uses `http://127.0.0.1:8080/mcp`; `khpi5` uses `http://127.0.0.1:9092` for work started on that host.
- **Tool discovery is mandatory, not optional.** Do not assume a tool exists or doesn't exist — call `retrieve_tools` on the local MCPProxy at the moment you need a capability. Use exact `server:tool` names and verify the server name before every call, especially before any write.
- Use Telegram/email MCP surfaces only for explicit delivery proof tasks, and never expose recipient details.
- Nango surfaces are not primary unless the task explicitly involves email/calendar/Notion/GitHub proof. Pick the correct account before any write.
- Appwrite is not part of this repo.

### Signed-in Edge Browser (Windows MCPProxy only)
For authenticated-browser tasks (the web UI, signed-in sites), use the MCPProxy upstream `playwright-edge` — Microsoft's official Playwright Extension attached to the live Edge `Default` profile (`David M` / `davidm@live.co.uk`). **This route exists only on the Windows MCPProxy (`http://127.0.0.1:8080/mcp`) — khpi5 has no signed-in browser route.** Never use Edge debugging mode, port 9222, or profile clones. Canonical runbook: `C:\Users\Dave\repos\windows\mcpproxy\signed-in-edge-automation.md`; prove health with `Test-SignedInEdgeAutomation.ps1 -RequireLiveProof` before first use (operational, full gate + authenticated identity readback verified 2026-08-30). Core rule 2 stands: never perform live lock-affecting actions via any browser or MCP surface unless the user explicitly asks.

## Core Rules

1. Prefer tests and local mocks before touching live locks or notification channels.
2. Never perform live lock-affecting actions unless the user explicitly asks.
3. Keep security-sensitive logs and tokens out of git.
4. Stage only intentional files; never `git add -A`.

