# Libraries

> **Navigation aid.** Library inventory extracted via AST. Read the source files listed here before modifying exported functions.

**79 library files** across 2 modules

## Pr_agent (78 files)

- `pr_agent/algo/utils.py` — get_model, get_setting, emphasize_header, unique_strings, convert_to_markdown_v2, extract_relevant_lines_str, …
- `pr_agent/servers/github_app.py` — handle_closed_pr, get_log_context, is_bot_user, should_process_pr_logic, handle_line_comments, start, …
- `pr_agent/git_providers/gerrit_provider.py` — clone, fetch, checkout, show, diff, reset_local_changes, …
- `pr_agent/tools/pr_help_docs.py` — modify_answer_section, extract_model_answer_and_relevant_sources, get_maximal_text_input_length_for_token_count_estimation, return_document_headings, map_documentation_files_to_contents, aggregate_documentation_files_for_prompt_contents, …
- `pr_agent/algo/git_patch_processing.py` — extend_patch, decode_if_bytes, should_skip_patch, process_patch_lines, check_if_hunk_lines_matches_to_file, extract_hunk_headers, …
- `pr_agent/algo/pr_processing.py` — cap_and_log_extra_lines, get_pr_diff, get_pr_diff_multiple_patchs, pr_generate_extended_diff, pr_generate_compressed_diff, generate_full_patch, …
- `pr_agent/servers/bitbucket_app.py` — is_bot_user, should_process_pr_logic, start, get_bearer_token, handle_manifest, handle_github_webhooks, …
- `pr_agent/servers/gitlab_webhook.py` — is_bot_user, is_draft, is_draft_ready, should_process_pr_logic, handle_ask_line, start, …
- `pr_agent/servers/github_polling.py` — now, run_handle_request, process_comment_sync, mark_notification_as_read, async_handle_request, process_comment, …
- `pr_agent/servers/gitea_app.py` — should_process_pr_logic, start, handle_gitea_webhooks, get_body, handle_request, handle_pr_event, …
- `pr_agent/log/__init__.py` — json_format, analytics_filter, inv_analytics_filter, setup_logger, get_logger, LoggingFormat
- `pr_agent/servers/azuredevops_server_webhook.py` — handle_line_comment, start, handle_request_comment, handle_request_azure, handle_webhook, root
- `pr_agent/servers/bitbucket_server_webhook.py` — handle_request, should_process_pr_logic, start, redirect_to_webhook, handle_webhook, root
- `pr_agent/servers/gerrit_server.py` — start, handle_gerrit_request, get_body, root, Action, Item
- `pr_agent/tools/ticket_pr_compliance_check.py` — find_jira_tickets, extract_ticket_links_from_pr_description, extract_ticket_links_from_branch_name, check_tickets_relevancy, extract_tickets, extract_and_cache_pr_tickets
- `pr_agent/algo/skills_loader.py` — discover_skills, format_skills_context, get_skills_context, SkillResource, Skill
- `pr_agent/git_providers/git_provider.py` — get_cached_global_settings, get_git_ssl_env, get_main_pr_language, GitProvider, IncrementalPR
- `pr_agent/tools/pr_description.py` — sanitize_diagram, count_chars_without_html, insert_br_after_x_chars, replace_code_tags, PRDescription
- `pr_agent/tools/pr_similar_issue.py` — PRSimilarIssue, IssueLevel, Metadata, Record, Corpus
- `pr_agent/algo/ai_handlers/base_ai_handler.py` — ModelInferenceSettings, ChatCompletionResult, BaseAiHandler
- `pr_agent/algo/artifacts.py` — resolve_artifact_path, format_artifact_content, load_artifact
- `pr_agent/algo/language_handler.py` — filter_bad_extensions, is_valid_file, sort_files_by_main_languages
- `pr_agent/algo/repo_context.py` — render_instruction_files, render_instruction_files_with_line_budget, build_repo_context
- `pr_agent/algo/token_handler.py` — ModelTypeValidator, TokenEncoder, TokenHandler
- `pr_agent/cli.py` — set_parser, run_command, run
- _…and 53 more files_

## Scripts (1 files)

- `scripts/set_pyproject_version.py` — main

---
_Back to [overview.md](./overview.md)_