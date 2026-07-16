# Project Context

This is a python project using fastapi.

The API has 10 routes. See .codesight/routes.md for the full route map with methods, paths, and tags.
Middleware includes: custom.

High-impact files (most imported, changes here affect many other files):
- //algo/utils.py (imported by 6 files)
- //config_loader.py (imported by 6 files)
- //log.py (imported by 6 files)
- /git_provider.py (imported by 6 files)
- //algo/file_filter.py (imported by 5 files)
- //algo/language_handler.py (imported by 5 files)
- //algo/git_patch_processing.py (imported by 3 files)
- //algo/types.py (imported by 2 files)

Required environment variables (no defaults):
- AGENT_CARD_HOST (pr_agent/mosaico/card.py)
- AGENT_CARD_PORT (pr_agent/mosaico/card.py)
- API_BASE (tests/unittest/test_mosaico_a2a_roundtrip.py)
- API_KEY (tests/unittest/test_mosaico_a2a_roundtrip.py)
- ARTIFACT_INSTRUCTIONS (pr_agent/servers/github_action_runner.py)
- ARTIFACT_PATH (pr_agent/servers/github_action_runner.py)
- AUTO_CAST_FOR_DYNACONF (pr_agent/git_providers/utils.py)
- AWS_ACCESS_KEY_ID (pr_agent/algo/ai_handlers/litellm_ai_handler.py)
- AWS_REGION_NAME (pr_agent/algo/ai_handlers/litellm_ai_handler.py)
- AWS_SECRET_ACCESS_KEY (pr_agent/algo/ai_handlers/litellm_ai_handler.py)
- AWS_SESSION_TOKEN (pr_agent/algo/ai_handlers/litellm_ai_handler.py)
- AWS_USE_IMDS (pr_agent/algo/ai_handlers/litellm_ai_handler.py)
- CODESTRAL_API_KEY (pr_agent/algo/ai_handlers/litellm_ai_handler.py)
- DATABRICKS_API_BASE (pr_agent/algo/ai_handlers/litellm_ai_handler.py)
- DATABRICKS_API_KEY (pr_agent/algo/ai_handlers/litellm_ai_handler.py)

See .codesight/cicd.md for additional cicd context.

Read .codesight/wiki/index.md for orientation (WHERE things live). Then read actual source files before implementing. Wiki articles are navigation aids, not implementation guides.
Read .codesight/CODESIGHT.md for the complete AI context map including all routes, schema, components, libraries, config, middleware, and dependency graph.
