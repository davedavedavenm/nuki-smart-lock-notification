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
