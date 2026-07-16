# Payments

> **Navigation aid.** Route list and file locations extracted via AST. Read the source files listed below before implementing or modifying this subsystem.

The Payments subsystem handles **2 routes** and touches: auth, payment.

## Routes

- `POST` `/webhook` → in: BackgroundTasks [auth, payment]
  `pr_agent/servers/bitbucket_app.py`
- `GET` `/webhook` [auth, payment]
  `pr_agent/servers/bitbucket_app.py`

## Source Files

Read these before implementing or modifying this subsystem:
- `pr_agent/servers/bitbucket_app.py`

---
_Back to [overview.md](./overview.md)_