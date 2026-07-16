# Bitbucket_app

> **Navigation aid.** Route list and file locations extracted via AST. Read the source files listed below before implementing or modifying this subsystem.

The Bitbucket_app subsystem handles **2 routes** and touches: auth, payment.

## Routes

- `POST` `/installed` → in: BackgroundTasks [auth, payment]
  `pr_agent/servers/bitbucket_app.py`
- `POST` `/uninstalled` → in: BackgroundTasks [auth, payment]
  `pr_agent/servers/bitbucket_app.py`

## Source Files

Read these before implementing or modifying this subsystem:
- `pr_agent/servers/bitbucket_app.py`

---
_Back to [overview.md](./overview.md)_