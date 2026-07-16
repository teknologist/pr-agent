# Infra

> **Navigation aid.** Route list and file locations extracted via AST. Read the source files listed below before implementing or modifying this subsystem.

The Infra subsystem handles **2 routes** and touches: auth, payment.

## Routes

- `POST` `/` [auth, payment]
  `pr_agent/servers/azuredevops_server_webhook.py`
- `GET` `/` [auth, payment]
  `pr_agent/servers/azuredevops_server_webhook.py`

## Source Files

Read these before implementing or modifying this subsystem:
- `pr_agent/servers/azuredevops_server_webhook.py`

---
_Back to [overview.md](./overview.md)_