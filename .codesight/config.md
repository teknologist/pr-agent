# Config

## Environment Variables

- `AGENT_CARD_HOST` **required** — pr_agent/mosaico/card.py
- `AGENT_CARD_PORT` **required** — pr_agent/mosaico/card.py
- `API_BASE` **required** — tests/unittest/test_mosaico_a2a_roundtrip.py
- `API_KEY` **required** — tests/unittest/test_mosaico_a2a_roundtrip.py
- `ARTIFACT_INSTRUCTIONS` **required** — pr_agent/servers/github_action_runner.py
- `ARTIFACT_PATH` **required** — pr_agent/servers/github_action_runner.py
- `AUTO_CAST_FOR_DYNACONF` **required** — pr_agent/git_providers/utils.py
- `AWS_ACCESS_KEY_ID` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `AWS_REGION_NAME` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `AWS_SECRET_ACCESS_KEY` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `AWS_SESSION_TOKEN` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `AWS_USE_IMDS` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `CODESTRAL_API_KEY` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `DATABRICKS_API_BASE` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `DATABRICKS_API_KEY` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `DEEPINFRA_API_KEY` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `DEEPSEEK_API_KEY` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `GEMINI_API_KEY` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `GIT_SSL_CAINFO` **required** — pr_agent/git_providers/git_provider.py
- `GITHUB_EVENT_NAME` **required** — pr_agent/servers/github_action_runner.py
- `GITHUB_EVENT_PATH` **required** — pr_agent/servers/github_action_runner.py
- `GITHUB_OUTPUT` **required** — pr_agent/algo/utils.py
- `GITHUB_TOKEN` **required** — pr_agent/servers/github_action_runner.py
- `GITHUB_WORKSPACE` **required** — pr_agent/algo/artifacts.py
- `GUNICORN_WORKERS` **required** — pr_agent/servers/gunicorn_config.py
- `HOST` **required** — pr_agent/mosaico/server.py
- `LOG_LEVEL` **required** — pr_agent/cli.py
- `LOG_SANE` **required** — pr_agent/log/__init__.py
- `MISTRAL_API_KEY` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `OPENAI_API_BASE` **required** — tests/e2e_tests/langchain_ai_handler.py
- `OPENAI_API_KEY` **required** — tests/e2e_tests/langchain_ai_handler.py
- `OPENAI_API_TYPE` **required** — tests/e2e_tests/langchain_ai_handler.py
- `OPENAI_KEY` **required** — pr_agent/servers/github_action_runner.py
- `OPENAI_ORG` **required** — pr_agent/servers/github_action_runner.py
- `OPENROUTER_API_BASE` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `OPENROUTER_API_KEY` **required** — pr_agent/algo/ai_handlers/litellm_ai_handler.py
- `PORT` **required** — pr_agent/mosaico/card.py
- `PR_AGENT_ARTIFACT_INSTRUCTIONS` **required** — pr_agent/servers/github_action_runner.py
- `PR_AGENT_ARTIFACT_PATH` **required** — pr_agent/servers/github_action_runner.py
- `PR_AGENT_CONFIG_BRANCH` **required** — pr_agent/cli.py
- `PR_AGENT_EXTRA_CONFIG_AUTH_HEADER` **required** — pr_agent/git_providers/utils.py
- `PR_AGENT_EXTRA_CONFIG_URL` **required** — pr_agent/cli.py
- `REQUESTS_CA_BUNDLE` **required** — pr_agent/git_providers/git_provider.py
- `SSL_CERT_FILE` **required** — pr_agent/git_providers/git_provider.py
- `TEST_PR_URL` **required** — tests/health_test/main.py

## Config Files

- `pyproject.toml`
