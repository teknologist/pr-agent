# pr-agent — Overview

> **Navigation aid.** This article shows WHERE things live (routes, models, files). Read actual source files before implementing new features or making changes.

**pr-agent** is a python project built with fastapi.

## Scale

10 API routes · 80 library files · 4 middleware layers · 45 environment variables

## Subsystems

- **[Payments](./payments.md)** — 2 routes — touches: auth, payment
- **[Bitbucket_app](./bitbucket_app.md)** — 2 routes — touches: auth, payment
- **[Gerrit_server](./gerrit_server.md)** — 1 routes
- **[Gitea_app](./gitea_app.md)** — 1 routes — touches: auth, payment
- **[Github_app](./github_app.md)** — 2 routes — touches: auth, payment
- **[Infra](./infra.md)** — 2 routes — touches: auth, payment

**Libraries:** 80 files — see [libraries.md](./libraries.md)

## High-Impact Files

Changes to these files have the widest blast radius across the codebase:

- `//algo/utils.py` — imported by **6** files
- `//config_loader.py` — imported by **6** files
- `//log.py` — imported by **6** files
- `/git_provider.py` — imported by **6** files
- `//algo/file_filter.py` — imported by **5** files
- `//algo/language_handler.py` — imported by **5** files

## Required Environment Variables

- `AGENT_CARD_HOST` — `pr_agent/mosaico/card.py`
- `AGENT_CARD_PORT` — `pr_agent/mosaico/card.py`
- `API_BASE` — `tests/unittest/test_mosaico_a2a_roundtrip.py`
- `API_KEY` — `tests/unittest/test_mosaico_a2a_roundtrip.py`
- `ARTIFACT_INSTRUCTIONS` — `pr_agent/servers/github_action_runner.py`
- `ARTIFACT_PATH` — `pr_agent/servers/github_action_runner.py`
- `AUTO_CAST_FOR_DYNACONF` — `pr_agent/git_providers/utils.py`
- `AWS_ACCESS_KEY_ID` — `pr_agent/algo/ai_handlers/litellm_ai_handler.py`
- `AWS_REGION_NAME` — `pr_agent/algo/ai_handlers/litellm_ai_handler.py`
- `AWS_SECRET_ACCESS_KEY` — `pr_agent/algo/ai_handlers/litellm_ai_handler.py`
- `AWS_SESSION_TOKEN` — `pr_agent/algo/ai_handlers/litellm_ai_handler.py`
- `AWS_USE_IMDS` — `pr_agent/algo/ai_handlers/litellm_ai_handler.py`
- _...33 more_

---
_Back to [index.md](./index.md) · Generated 2026-07-16_