# Github_app

> **Navigation aid.** Route list and file locations extracted via AST. Read the source files listed below before implementing or modifying this subsystem.

The Github_app subsystem handles **2 routes** and touches: auth, payment.

## Routes

- `POST` `/api/v1/github_webhooks` → in: BackgroundTasks [auth, payment]
  `pr_agent/servers/github_app.py`
- `POST` `/api/v1/marketplace_webhooks` → in: BackgroundTasks [auth, payment]
  `pr_agent/servers/github_app.py`

## Source Files

Read these before implementing or modifying this subsystem:
- `pr_agent/servers/github_app.py`

---
_Back to [overview.md](./overview.md)_