# pr-agent — AI Context Map

> **Stack:** fastapi | none | unknown | python

> 10 routes | 0 models | 0 components | 80 lib files | 45 env vars | 4 middleware | 20% test coverage
> **Token savings:** this file is ~6,700 tokens. Without it, AI exploration would cost ~39,800 tokens. **Saves ~33,200 tokens per conversation.**
> **Last scanned:** 2026-07-16 20:17 — re-run after significant changes

---

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

---

# Libraries

- `pr_agent/agent/pr_agent.py` — class PRAgent
- `pr_agent/algo/ai_handlers/base_ai_handler.py`
  - class ModelInferenceSettings
  - class ChatCompletionResult
  - class BaseAiHandler
- `pr_agent/algo/ai_handlers/langchain_ai_handler.py` — class LangChainOpenAIHandler
- `pr_agent/algo/ai_handlers/litellm_ai_handler.py` — class LiteLLMAIHandler
- `pr_agent/algo/ai_handlers/litellm_helpers.py` — class MockResponse
- `pr_agent/algo/ai_handlers/openai_ai_handler.py` — class OpenAIHandler
- `pr_agent/algo/artifacts.py`
  - function resolve_artifact_path: (path) -> Optional[Path]
  - function format_artifact_content: (content, label, instructions) -> str
  - function load_artifact: () -> str
- `pr_agent/algo/cli_args.py` — class CliArgs
- `pr_agent/algo/file_filter.py` — function filter_ignored: (files, platform), function translate_globs_to_regexes: (globs)
- `pr_agent/algo/git_patch_processing.py`
  - function extend_patch: (original_file_str, patch_str, patch_extra_lines_before, patch_extra_lines_after, filename, new_file_str) -> str
  - function decode_if_bytes: (original_file_str)
  - function should_skip_patch: (filename)
  - function process_patch_lines: (patch_str, original_file_str, patch_extra_lines_before, patch_extra_lines_after, new_file_str)
  - function check_if_hunk_lines_matches_to_file: (i, original_lines, patch_lines, start1)
  - function extract_hunk_headers: (match)
  - _...4 more_
- `pr_agent/algo/language_handler.py`
  - function filter_bad_extensions: (files)
  - function is_valid_file: (filename, bad_extensions) -> bool
  - function sort_files_by_main_languages: (languages, files)
- `pr_agent/algo/pr_processing.py`
  - function cap_and_log_extra_lines: (value, direction) -> int
  - function get_pr_diff: (git_provider, token_handler, model, add_line_numbers_to_hunks, disable_extra_lines, large_pr_handling, return_remaining_files)
  - function get_pr_diff_multiple_patchs: (git_provider, token_handler, model, add_line_numbers_to_hunks, disable_extra_lines)
  - function pr_generate_extended_diff: (pr_languages, token_handler, add_line_numbers_to_hunks, patch_extra_lines_before, patch_extra_lines_after) -> Tuple[list, int, list]
  - function pr_generate_compressed_diff: (top_langs, token_handler, model, convert_hunks_to_line_numbers, large_pr_handling) -> Tuple[list, list, list, list, dict, list]
  - function generate_full_patch: (convert_hunks_to_line_numbers, file_dict, max_tokens_model, remaining_files_list_prev, token_handler)
  - _...4 more_
- `pr_agent/algo/repo_context.py`
  - function render_instruction_files: (files, str]) -> str
  - function render_instruction_files_with_line_budget: (files, str], max_lines) -> str
  - function build_repo_context: (git_provider) -> str
- `pr_agent/algo/skills_loader.py`
  - function discover_skills: (paths) -> List[Skill]
  - function format_skills_context: (skills, max_tokens) -> str
  - function get_skills_context: () -> str
  - class SkillResource
  - class Skill
- `pr_agent/algo/token_handler.py`
  - class ModelTypeValidator
  - class TokenEncoder
  - class TokenHandler
- `pr_agent/algo/types.py` — class EDIT_TYPE, class FilePatchInfo
- `pr_agent/algo/utils.py`
  - function get_model: (model_type) -> str
  - function get_setting: (key) -> Any
  - function emphasize_header: (text, only_markdown, reference_link) -> str
  - function unique_strings: (input_list) -> List[str]
  - function convert_to_markdown_v2: (output_data, gfm_supported, incremental_review, git_provider, files) -> str
  - function extract_relevant_lines_str: (end_line, files, relevant_file, start_line, dedent) -> str
  - _...35 more_
- `pr_agent/cli.py`
  - function set_parser: ()
  - function run_command: (pr_url, command)
  - function run: (inargs, args)
- `pr_agent/cli_pip.py` — function main: ()
- `pr_agent/config_loader.py`
  - function get_settings: (use_context)
  - function apply_secrets_manager_config: ()
  - function apply_secrets_to_config: (secrets)
- `pr_agent/custom_merge_loader.py` — function load: (obj, env, silent, key, filename), function validate_file_security: (file_data, filename)
- `pr_agent/git_providers/__init__.py` — function get_git_provider: (), function get_git_provider_with_context: (pr_url) -> GitProvider
- `pr_agent/git_providers/azuredevops_provider.py` — class AzureDevopsProvider
- `pr_agent/git_providers/bitbucket_provider.py` — class BitbucketProvider
- `pr_agent/git_providers/bitbucket_server_provider.py` — class BitbucketServerProvider
- `pr_agent/git_providers/codecommit_client.py`
  - class CodeCommitDifferencesResponse
  - class CodeCommitPullRequestResponse
  - class CodeCommitClient
- `pr_agent/git_providers/codecommit_provider.py`
  - class PullRequestCCMimic
  - class CodeCommitFile
  - class CodeCommitProvider
- `pr_agent/git_providers/diff_parsing.py`
  - function to_hunk_only_patch: (patch_str) -> str
  - function parse_unified_diff: (diff_text) -> list[FilePatchInfo]
  - function reconstruct_base_file: (head_file_str, patch_str) -> str
- `pr_agent/git_providers/gerrit_provider.py`
  - function clone: (url, directory)
  - function fetch: (url, refspec, cwd)
  - function checkout: (cwd)
  - function show: (*args, cwd)
  - function diff: (*args, cwd)
  - function reset_local_changes: (cwd)
  - _...7 more_
- `pr_agent/git_providers/git_provider.py`
  - function get_cached_global_settings: (cache_key, fetch_fn)
  - function get_git_ssl_env: () -> dict[str, str]
  - function get_main_pr_language: (languages, files) -> str
  - class GitProvider
  - class IncrementalPR
- `pr_agent/git_providers/gitea_provider.py` — class GiteaProvider, class RepoApi
- `pr_agent/git_providers/github_provider.py` — class GithubProvider
- `pr_agent/git_providers/gitlab_provider.py` — class DiffNotFoundError, class GitLabProvider
- `pr_agent/git_providers/local_git_provider.py` — class PullRequestMimic, class LocalGitProvider
- `pr_agent/git_providers/plain_diff_provider.py` — class PullRequestMimic, class PlainDiffGitProvider
- `pr_agent/git_providers/utils.py`
  - function apply_repo_settings: (pr_url)
  - function handle_configurations_errors: (config_errors, git_provider)
  - function set_claude_model: ()
- `pr_agent/identity_providers/__init__.py` — function get_identity_provider: ()
- `pr_agent/identity_providers/default_identity_provider.py` — class DefaultIdentityProvider
- `pr_agent/identity_providers/identity_provider.py` — class Eligibility, class IdentityProvider
- `pr_agent/log/__init__.py`
  - function json_format: (record) -> str
  - function analytics_filter: (record) -> bool
  - function inv_analytics_filter: (record) -> bool
  - function setup_logger: (level, fmt)
  - function get_logger: (*args, **kwargs)
  - class LoggingFormat
- `pr_agent/mosaico/card.py` — function build_agent_card: () -> AgentCard
- `pr_agent/mosaico/diff_provider.py` — function parse_unified_diff: (diff_text) -> List[FilePatchInfo], class DiffInputProvider
- `pr_agent/mosaico/dispatch.py`
  - function route_and_run_result: (user_text) -> "RouteResult"
  - function route_and_run: (user_text) -> str
  - class RouteResult
- `pr_agent/mosaico/env_bridge.py` — function langfuse_env_present: () -> bool, function apply_mosaico_env: () -> None
- `pr_agent/mosaico/executor.py` — function health_check: () -> str, class PRAgentExecutor
- `pr_agent/mosaico/observability.py`
  - function parse_observability_metadata: (raw) -> dict
  - function mosaico_log_context: (meta, context_id)
  - function langfuse_span: (meta, context_id)
- `pr_agent/mosaico/server.py` — function build_app: (), function start: () -> None
- `pr_agent/secret_providers/__init__.py` — function get_secret_provider: ()
- `pr_agent/secret_providers/aws_secrets_manager_provider.py` — class AWSSecretsManagerProvider
- `pr_agent/secret_providers/google_cloud_storage_secret_provider.py` — class GoogleCloudStorageSecretProvider
- `pr_agent/secret_providers/secret_provider.py` — class SecretProvider
- `pr_agent/servers/azuredevops_server_webhook.py`
  - function handle_line_comment: (body, thread_id, provider)
  - function start: ()
  - function handle_request_comment: (url, body, thread_id, comment_id, log_context)
  - function handle_request_azure: (data, log_context)
  - function handle_webhook: (background_tasks, request)
  - function root: ()
- `pr_agent/servers/bitbucket_app.py`
  - function is_bot_user: (data) -> bool
  - function should_process_pr_logic: (data) -> bool
  - function start: ()
  - function get_bearer_token: (shared_secret, client_key)
  - function handle_manifest: (request, response)
  - function handle_github_webhooks: (background_tasks, request)
  - _...3 more_
- `pr_agent/servers/bitbucket_server_webhook.py`
  - function handle_request: (background_tasks, url, body, log_context)
  - function should_process_pr_logic: (data) -> bool
  - function start: ()
  - function redirect_to_webhook: ()
  - function handle_webhook: (background_tasks, request)
  - function root: ()
- `pr_agent/servers/gerrit_server.py`
  - function start: ()
  - function handle_gerrit_request: (action, item)
  - function get_body: (request)
  - function root: ()
  - class Action
  - class Item
- `pr_agent/servers/gitea_app.py`
  - function should_process_pr_logic: (body) -> bool
  - function start: ()
  - function handle_gitea_webhooks: (background_tasks, request, response)
  - function get_body: (request)
  - function handle_request: (body, Any], event)
  - function handle_pr_event: (body, Any], event, action, agent)
  - _...1 more_
- `pr_agent/servers/github_action_runner.py`
  - function is_true: (value, bool]) -> bool
  - function get_setting_or_env: (key, default, bool]) -> Union[str, bool]
  - function run_action: ()
- `pr_agent/servers/github_app.py`
  - function handle_closed_pr: (body, event, action, log_context)
  - function get_log_context: (body, event, action, build_number)
  - function is_bot_user: (sender, sender_type)
  - function should_process_pr_logic: (body) -> bool
  - function handle_line_comments: (body, comment_body, Any]) -> str
  - function start: ()
  - _...8 more_
- `pr_agent/servers/github_lambda_webhook.py` — function lambda_handler: (event, context)
- `pr_agent/servers/github_polling.py`
  - function now: () -> str
  - function run_handle_request: (pr_url, rest_of_comment, comment_id, git_provider)
  - function process_comment_sync: (pr_url, rest_of_comment, comment_id)
  - function mark_notification_as_read: (headers, notification, session)
  - function async_handle_request: (pr_url, rest_of_comment, comment_id, git_provider)
  - function process_comment: (pr_url, rest_of_comment, comment_id)
  - _...2 more_
- `pr_agent/servers/gitlab_lambda_webhook.py` — function lambda_handler: (event, context)
- `pr_agent/servers/gitlab_webhook.py`
  - function is_bot_user: (data) -> bool
  - function is_draft: (data) -> bool
  - function is_draft_ready: (data) -> bool
  - function should_process_pr_logic: (data) -> bool
  - function handle_ask_line: (body, data)
  - function start: ()
  - _...3 more_
- `pr_agent/servers/help.py` — class HelpMessage
- `pr_agent/servers/utils.py`
  - function verify_signature: (payload_body, secret_token, signature_header)
  - class RateLimitExceeded
  - class DefaultDictWithTimeout
- `pr_agent/tools/council_review.py`
  - function resolve_council_review_config: () -> CouncilReviewConfig
  - class CouncilModelConfig
  - class CouncilReviewConfig
  - class CouncilMemberReview
  - class CouncilPeerEvaluation
  - class CouncilReviewResult
  - _...2 more_
- `pr_agent/tools/pr_add_docs.py` — function get_docs_for_language: (language, style), class PRAddDocs
- `pr_agent/tools/pr_code_suggestions.py` — class PRCodeSuggestions
- `pr_agent/tools/pr_config.py` — class PRConfig
- `pr_agent/tools/pr_description.py`
  - function sanitize_diagram: (diagram_raw) -> str
  - function count_chars_without_html: (string)
  - function insert_br_after_x_chars: (text, x)
  - function replace_code_tags: (text)
  - class PRDescription
- `pr_agent/tools/pr_generate_labels.py` — class PRGenerateLabels
- `pr_agent/tools/pr_help_docs.py`
  - function modify_answer_section: (ai_response) -> str | None
  - function extract_model_answer_and_relevant_sources: (ai_response) -> str | None
  - function get_maximal_text_input_length_for_token_count_estimation: ()
  - function return_document_headings: (text, ext) -> str
  - function map_documentation_files_to_contents: (base_path, doc_files, max_allowed_file_len) -> dict[str, str]
  - function aggregate_documentation_files_for_prompt_contents: (file_path_to_contents, str], return_just_headings) -> str
  - _...5 more_
- `pr_agent/tools/pr_help_message.py`
  - function extract_header: (snippet)
  - function generate_bbdc_table: (column_arr_1, column_arr_2)
  - class PRHelpMessage
- `pr_agent/tools/pr_line_questions.py` — class PR_LineQuestions
- `pr_agent/tools/pr_questions.py` — class PRQuestions
- `pr_agent/tools/pr_reviewer.py` — class PRReviewer
- `pr_agent/tools/pr_similar_issue.py`
  - class PRSimilarIssue
  - class IssueLevel
  - class Metadata
  - class Record
  - class Corpus
- `pr_agent/tools/pr_update_changelog.py` — class PRUpdateChangelog
- `pr_agent/tools/progress_comment.py`
  - function get_progress_gif_url: () -> str
  - function get_progress_gif_width: () -> int
  - function build_progress_comment: () -> str
- `pr_agent/tools/ticket_pr_compliance_check.py`
  - function find_jira_tickets: (text)
  - function extract_ticket_links_from_pr_description: (pr_description, repo_path, base_url_html)
  - function extract_ticket_links_from_branch_name: (branch_name, repo_path, base_url_html)
  - function check_tickets_relevancy: ()
  - function extract_tickets: (git_provider)
  - function extract_and_cache_pr_tickets: (git_provider, vars)
- `scripts/set_pyproject_version.py` — function main: () -> None

---

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

---

# Middleware

## custom
- compression_strategy — `docs/docs/core-abilities/compression_strategy.md`
- generate_labels — `docs/docs/tools/generate_labels.md`
- pr_generate_labels — `pr_agent/tools/pr_generate_labels.py`
- test_litellm_api_key_guard — `tests/unittest/test_litellm_api_key_guard.py`

---

# Dependency Graph

## Most Imported Files (change these carefully)

- `//algo/utils.py` — imported by **6** files
- `//config_loader.py` — imported by **6** files
- `//log.py` — imported by **6** files
- `/git_provider.py` — imported by **6** files
- `//algo/file_filter.py` — imported by **5** files
- `//algo/language_handler.py` — imported by **5** files
- `//algo/git_patch_processing.py` — imported by **3** files
- `//algo/types.py` — imported by **2** files
- `//servers/utils.py` — imported by **1** files

## Import Map (who imports what)

- `//algo/utils.py` ← `pr_agent/git_providers/azuredevops_provider.py`, `pr_agent/git_providers/bitbucket_provider.py`, `pr_agent/git_providers/bitbucket_server_provider.py`, `pr_agent/git_providers/codecommit_provider.py`, `pr_agent/git_providers/github_provider.py` +1 more
- `//config_loader.py` ← `pr_agent/git_providers/azuredevops_provider.py`, `pr_agent/git_providers/bitbucket_provider.py`, `pr_agent/git_providers/bitbucket_server_provider.py`, `pr_agent/git_providers/codecommit_provider.py`, `pr_agent/git_providers/github_provider.py` +1 more
- `//log.py` ← `pr_agent/git_providers/azuredevops_provider.py`, `pr_agent/git_providers/bitbucket_provider.py`, `pr_agent/git_providers/bitbucket_server_provider.py`, `pr_agent/git_providers/codecommit_provider.py`, `pr_agent/git_providers/github_provider.py` +1 more
- `/git_provider.py` ← `pr_agent/git_providers/azuredevops_provider.py`, `pr_agent/git_providers/bitbucket_provider.py`, `pr_agent/git_providers/bitbucket_server_provider.py`, `pr_agent/git_providers/codecommit_provider.py`, `pr_agent/git_providers/github_provider.py` +1 more
- `//algo/file_filter.py` ← `pr_agent/git_providers/azuredevops_provider.py`, `pr_agent/git_providers/bitbucket_provider.py`, `pr_agent/git_providers/bitbucket_server_provider.py`, `pr_agent/git_providers/github_provider.py`, `pr_agent/git_providers/gitlab_provider.py`
- `//algo/language_handler.py` ← `pr_agent/git_providers/azuredevops_provider.py`, `pr_agent/git_providers/bitbucket_provider.py`, `pr_agent/git_providers/bitbucket_server_provider.py`, `pr_agent/git_providers/github_provider.py`, `pr_agent/git_providers/gitlab_provider.py`
- `//algo/git_patch_processing.py` ← `pr_agent/git_providers/bitbucket_server_provider.py`, `pr_agent/git_providers/github_provider.py`, `pr_agent/git_providers/gitlab_provider.py`
- `//algo/types.py` ← `pr_agent/git_providers/bitbucket_server_provider.py`, `pr_agent/git_providers/github_provider.py`
- `//servers/utils.py` ← `pr_agent/git_providers/github_provider.py`

---

# Test Coverage

> **20%** of routes and models are covered by tests
> 100 test files found

## Covered Routes

- POST:/
- GET:/

---

# CI/CD Pipelines

## GitHub Actions (9 workflows)

| Workflow | Triggers | Jobs | Deploy | Environments |
|---|---|---|---|---|
| Build-and-test | push, pull_request | 1 | — | — |
| Code-coverage | workflow_dispatch, pull_request | 1 | — | — |
| CodeQL | push, pull_request, schedule | 1 | — | — |
| docs-ci | push | 1 | — | — |
| PR-Agent E2E tests | workflow_dispatch | 1 | — | — |
| PR-Agent | workflow_dispatch | 1 | — | — |
| pre-commit | workflow_dispatch | 1 | — | — |
| Publish | release, workflow_dispatch | 4 | — | release |
| Release Drafter | push, pull_request_target | 1 | — | — |

### Publish

> `.github/workflows/publish.yml`

> Concurrency: `publish-${{ github.event_name == 'release' && github.event.release.tag_name || format('v{0}', inputs.version) }}`

- **prepare** on `ubuntu-latest` — 2 steps
- **publish-pypi** on `ubuntu-latest` — 5 steps (needs: prepare)
  - `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5`
  - `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`
  - `pypa/gh-action-pypi-publish@cef221092ed1bacb1cc03d23a2d87d1d172e277b`
- **publish-docker** on `ubuntu-latest` — 9 steps (needs: prepare)
  - `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5`
  - `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`
  - `docker/setup-qemu-action@c7c53464625b32c7a7e944ae62b3e17d2b600130`
  - `docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f`
  - `docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9`
  - `docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8`
  - `actions/attest-build-provenance@977bb373ede98d70efdf65b84cb5f73e068dcc2a`
- **finalize** on `ubuntu-latest` — 7 steps (needs: prepare, publish-pypi, publish-docker)
  - `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5`
  - `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`

### Secrets

- `BITBUCKET_PASSWORD`
- `BITBUCKET_USERNAME`
- `CODECOV_TOKEN`
- `DOCKERHUB_TOKEN`
- `DOCKERHUB_USERNAME`
- `GITHUB_TOKEN`
- `OPENAI_KEY`
- `OPENAI_ORG`
- `PINECONE_API_KEY`
- `PINECONE_ENVIRONMENT`
- `PYPI_API_TOKEN`
- `TOKEN_GITHUB`
- `TOKEN_GITLAB`

---
_Source: .github/workflows/build-and-test.yaml, .github/workflows/code_coverage.yaml, .github/workflows/codeql.yml, .github/workflows/docs-ci.yaml, .github/workflows/e2e_tests.yaml, .github/workflows/pr-agent-review.yaml, .github/workflows/pre-commit.yml, .github/workflows/publish.yml, .github/workflows/release-drafter.yml_
_Generated by codesight-cicd-plugin_

---

_Generated by [codesight](https://github.com/Houseofmvps/codesight) — see your codebase clearly_