# Repository Guidelines

## Dos and Don’ts

- **Do** match the interpreter requirement declared in `pyproject.toml` (Python ≥ 3.12) and install `requirements.txt` plus `requirements-dev.txt` before running tools.
- **Do** run tests with `PYTHONPATH=.` set to keep imports functional (for example `PYTHONPATH=. ./.venv/bin/pytest tests/unittest/test_fix_json_escape_char.py -q`).
- **Do** adjust configuration through `.pr_agent.toml` or files under `pr_agent/settings/` instead of hard-coding values.
- **Don’t** commit secrets or access tokens; rely on environment variables as shown in the health and e2e tests.
- **Don’t** reformat or reorder files globally; match existing 120-character lines, import ordering, and docstring style.
- **Don’t** delete or rename configuration, prompt, or workflow files without maintainer approval.

## Project Structure and Module Organization

PR-Agent automates AI-assisted reviews for pull requests across multiple git providers.

- `pr_agent/agent/` orchestrates commands (`review`, `describe`, `improve`, etc.) via `pr_agent/agent/pr_agent.py`.
- `pr_agent/tools/` implements individual capabilities such as reviewers, code suggestions, docs updates, and label generation.
- `pr_agent/git_providers/` and `pr_agent/identity_providers/` handle integrations with GitHub, GitLab, Bitbucket, Azure DevOps, and secrets.
- `pr_agent/settings/` stores Dynaconf defaults (prompts, configuration templates, ignore lists) respected at runtime; `.pr_agent.toml` overrides repository-level behavior.
- `tests/unittest/`, `tests/e2e_tests/`, and `tests/health_test/` contain pytest-based unit, end-to-end, and smoke checks.
- `docs/` holds the MkDocs site (`docs/mkdocs.yml` plus content under `docs/docs/`); overrides live in `docs/overrides/`.
- `.github/workflows/` defines CI pipelines for unit tests, coverage, docs deployment, pre-commit, and PR-agent self-review.
- `docker/` and the root Dockerfiles provide build targets for services (`github_app`, `gitlab_webhook`, etc.) and the `test` stage used in CI.

## Build, Test, and Development Commands

- Create or activate a virtual environment, then install runtime dependencies with `pip install -r requirements.txt`; add development tooling via `pip install -r requirements-dev.txt`.
- Run a single unit test (verified): `PYTHONPATH=. ./.venv/bin/pytest tests/unittest/test_fix_json_escape_char.py -q`.
- Run the full unit suite: `PYTHONPATH=. ./.venv/bin/pytest tests/unittest -v`.
- Execute the CLI locally once dependencies and API keys are available: `python -m pr_agent.cli --pr_url <https://host/org/repo/pull/123> review`.
- Build the test Docker target mirror of CI when containerizing: `docker build -f docker/Dockerfile --target test .` (loads dev dependencies and copies `tests/`).
- Generate and deploy documentation with MkDocs after installing the same extras as CI (`mkdocs-material`, `mkdocs-glightbox`): `mkdocs serve -f docs/mkdocs.yml` for previews and `mkdocs gh-deploy -f docs/mkdocs.yml` for publication.

## Coding Style and Naming Conventions

- Python sources follow the Ruff configuration in `pyproject.toml` (`line-length = 120`, Pyflakes plus `flake8-bugbear` checks, and isort ordering). Keep imports grouped as isort would produce and prefer double quotes for strings.
- Pre-commit (`.pre-commit-config.yaml`) enforces trailing whitespace cleanup, final newlines, TOML/YAML validity, and optional `isort`; run `pre-commit run --all-files` before submitting patches if installed.
- Before committing, run `flake8` and fix every issue it reports. Keep fixes mechanical (rename, reformat, remove unused imports, add missing newlines); do not alter program logic while cleaning up—if a lint fix would change behavior, surface it instead of applying it silently.
- Match existing docstring and comment style—concise English comments using imperative phrasing only where necessary.
- Configuration files in `pr_agent/settings/` are TOML; preserve formatting, section order, and comments when editing prompts or defaults.
- Markdown in `docs/` uses MkDocs conventions (YAML front matter absent; rely on heading hierarchy already in place).

## Testing Guidelines

- Pytest is the standard framework; keep new tests under the closest matching directory (`tests/unittest/` for unit logic, `tests/e2e_tests/` for integration flows, `tests/health_test/` for smoke coverage).
- Prefer focused unit tests that isolate helpers in `pr_agent/algo/`, `pr_agent/tools/`, or provider adapters; use parameterized tests where existing files already do so.
- Set `PYTHONPATH=.` when invoking pytest from the repository root to avoid import errors.
- End-to-end suites require provider tokens (`TOKEN_GITHUB`, `TOKEN_GITLAB`, `BITBUCKET_USERNAME`, `BITBUCKET_PASSWORD`) and may take several minutes; run them only when credentials and sandboxes are configured.
- The health test (`tests/health_test/main.py`) exercises `/describe`, `/review`, and `/improve`; update expected artifacts if prompts change meaningfully.

## Commit and Pull Request Guidelines

- Follow `CONTRIBUTING.md`: keep changes focused, add or update tests, and use Conventional Commit-style messages (e.g., `fix: handle missing repo settings gracefully`).
- Target branch names follow `feature/<name>` or `fix/<issue>` patterns for substantial work.
- Reference related issues and update README or docs when user-facing behavior shifts.
- Ensure CI workflows (`build-and-test`, `code-coverage`, `docs-ci`) succeed locally or in draft PRs before requesting review; reproduce failures with the documented commands above.
- Include screenshots or terminal captures when modifying user-visible output or documentation previews.

## Safety and Permissions

- Ask for confirmation before adding dependencies, renaming files, or changing workflow definitions; many consumers embed these paths and prompts.
- Stay within existing formatting and directory conventions—avoid mass refactors, re-sorting of prompts, or reformatting Markdown beyond the touched sections.
- You may read files, list directories, and run targeted lint/test/doc commands without prior approval; coordinate before launching full Docker builds or e2e suites that rely on external credentials.
- Never commit cached credentials, API keys, or coverage artifacts; CI already handles secrets through GitHub Actions.
- Treat prompt and configuration files as single sources of truth—update mirrors (`.pr_agent.toml`, `pr_agent/settings/*.toml`) together when behavior changes.

## Security and Configuration Tips

- Secrets should be supplied through environment variables (see usages in `tests/e2e_tests/test_github_app.py` and `tests/health_test/main.py`); do not persist them in code or configuration files.
- Adjust runtime behavior by overriding keys in `.pr_agent.toml` or by supplying repository-specific Dynaconf files; keep overrides minimal and documented inside the PR description.
- Review `SECURITY.md` before disclosing vulnerabilities and follow its contact instructions for responsible reporting.

## Architecture and Runtime Guidance

PR-Agent is a CLI/server that runs AI-powered tools (`/review`, `/describe`, `/improve`, `/ask`, etc.) against pull requests on GitHub, GitLab, Bitbucket, Azure DevOps, Gitea, Gerrit, or local repositories. The main dispatch flow is `pr_agent/agent/pr_agent.py` → the `command2class` map → a tool class in `pr_agent/tools/`. Each tool fetches the pull request through a git provider, builds a Jinja2 prompt, calls the model, and publishes the result.

### Prompt building

Tools generally construct a `self.vars` dictionary in `__init__`, then pass it with system and user prompt strings to `TokenHandler`. Prompts are rendered with `jinja2.Environment(undefined=StrictUndefined)`, so every template variable must be present in `vars`; use `{%- if ... %}` guards rather than optional Jinja lookups.

Prompt strings live as TOML in `pr_agent/settings/`, loaded by Dynaconf into `global_settings`. Prompt files follow tool naming conventions: `pr_reviewer.py` ↔ `pr_reviewer_prompts.toml`, `pr_description.py` ↔ `pr_description_prompts.toml`, and `pr_code_suggestions.py` ↔ `code_suggestions/pr_code_suggestions_prompts.toml` (including the `_not_decoupled` variant). Register new prompt files in the `settings_files=[...]` list in `config_loader.py`.

### Settings and runtime configuration

`get_settings()` from `pr_agent/config_loader.py` is the single configuration accessor. It returns a request-scoped Dynaconf object from `starlette_context` for server flows or the module-level `global_settings` otherwise. Defaults live in `pr_agent/settings/configuration.toml`; per-repository overrides come from `.pr_agent.toml` and are merged by `pr_agent/git_providers/utils.py::apply_repo_settings` once per request before tool dispatch. Add new configuration sections to `configuration.toml` with comments; it is the authoritative option listing, and `apply_repo_settings` performs per-section merges so partial overrides work.

Sensitive values come from environment variables or gitignored `.secrets.toml`. `apply_secrets_manager_config()` can additionally load values from AWS Secrets Manager.

### Git providers

`pr_agent/git_providers/` contains one provider per platform. Providers share the `GitProvider` interface in `git_providers/git_provider.py`; capabilities are probed with `is_supported("feature")`. Tools should query capabilities instead of branching on `isinstance(provider, GithubProvider)`, because providers may stub or override features. Features such as semantic file types in `/describe` are gated by `gfm_markdown` support.

### Servers and entrypoints

`pr_agent/servers/` contains webhook entrypoints such as `github_app.py`, `gitlab_webhook.py`, and `bitbucket_app.py`. They translate webhooks into `PRAgent.handle_request(pr_url, command)` calls. The CLI entrypoint is `pr_agent/cli.py`, registered as the `pr-agent` console script.

### Additional test guidance

Unit tests in `tests/unittest/` are appropriate for helpers in `pr_agent/algo/`, prompt-building logic, and provider adapters; follow the surrounding `test_<module>.py` naming pattern and use `parametrize` where established. `tests/health_test/main.py` exercises `/describe`, `/review`, and `/improve` against real pull requests and is the canary for prompt regressions; update expected artifacts when prompts change meaningfully.

## Repository Conventions

Prompt and configuration TOMLs are single sources of truth. When behavior changes, update prompts and configuration defaults together rather than forking values across files. Keep prompt/config diffs focused: do not reformat or reorder unrelated lines.

Issues are tracked in the Linear project `pr-agent`; pull requests are not a triage request surface. Triage labels are `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. Domain documentation uses the single-context layout under `docs/agents/`.


# AI Context (auto-generated by codesight)

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
See .codesight/githooks.md for additional githooks context.

Read .codesight/wiki/index.md for orientation (WHERE things live). Then read actual source files before implementing. Wiki articles are navigation aids, not implementation guides.
Read .codesight/CODESIGHT.md for the complete AI context map including all routes, schema, components, libraries, config, middleware, and dependency graph.
