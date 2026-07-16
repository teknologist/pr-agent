# Routes

- `POST` `/` params() [auth, payment] ✓
- `GET` `/` params() [auth, payment] ✓
- `POST` `/webhook` params() → in: BackgroundTasks [auth, payment]
- `GET` `/webhook` params() [auth, payment]
- `POST` `/installed` params() → in: BackgroundTasks [auth, payment]
- `POST` `/uninstalled` params() → in: BackgroundTasks [auth, payment]
- `POST` `/api/v1/gerrit/{action}` params(action) → in: Action
- `POST` `/api/v1/gitea_webhooks` params() → in: BackgroundTasks [auth, payment]
- `POST` `/api/v1/github_webhooks` params() → in: BackgroundTasks [auth, payment]
- `POST` `/api/v1/marketplace_webhooks` params() → in: BackgroundTasks [auth, payment]
