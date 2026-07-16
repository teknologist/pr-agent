# Gitea_app

> **Navigation aid.** Route list and file locations extracted via AST. Read the source files listed below before implementing or modifying this subsystem.

The Gitea_app subsystem handles **1 routes** and touches: auth, payment.

## Routes

- `POST` `/api/v1/gitea_webhooks` → in: BackgroundTasks [auth, payment]
  `pr_agent/servers/gitea_app.py`

## Source Files

Read these before implementing or modifying this subsystem:
- `pr_agent/servers/gitea_app.py`

---
_Back to [overview.md](./overview.md)_