# Knowledge Map — pr-agent
> 51 notes · 1 decisions · 5 open questions

> **AI Primer:** This knowledge base has 51 notes. Key topics: example usage, configuration options, how it works, usage tips. Most recent decision: Use  `import x`  for importing packages and modules. 5 open questions remain.

## Key Decisions (1)
- Use  `import x`  for importing packages and modules.

## Open Questions (5)
- "PR-Agent removed the original description from the PR. Why"?
- Does the code logic cover relevant edge cases?
- Is the code logic clear and easy to understand?
- Is the code logic efficient?
- hasattr(obj, 'settings_files') for some reason returns False. Need to us, validate_file_security(), FakeDynaconf, Securi

## Recurring Themes
example usage · configuration options · how it works · usage tips · features · example results · corpus check · graph freshness · community hubs navigation · import cycles · hyperedges group relationships · communities 168 total 32 thin omitted

## People
@naorpeled · @company · @sha256

## Hub Notes (most referenced)
- `docs/docs/usage-guide/changing_a_model.md` — **9** incoming references — changing a model
- `docs/docs/core-abilities/interactivity.md` — **6** incoming references — Interactivity
- `docs/docs/tools/improve.md` — **5** incoming references — improve
- `docs/docs/usage-guide/configuration_options.md` — **5** incoming references — GitLab Personal Access Token
- `docs/docs/core-abilities/compression_strategy.md` — **4** incoming references — compression strategy
- `docs/docs/core-abilities/dynamic_context.md` — **4** incoming references — dynamic context
- `docs/docs/tools/describe.md` — **4** incoming references — describe
- `docs/docs/tools/help.md` — **4** incoming references — help
- `docs/docs/tools/index.md` — **4** incoming references — Tools
- `docs/docs/core-abilities/fetching_ticket_context.md` — **3** incoming references — Fetching Ticket Context for PRs

## Note Index (51)

### Specs & PRDs (14)
- `docs/docs/core-abilities/agent_skills.md` ← 1 refs — `Supported Tools: Review, Improve, Describe`
- `docs/docs/core-abilities/compression_strategy.md` ← 4 refs — `Supported Git Platforms: GitHub, GitLab, Bitbucket`
- `docs/docs/core-abilities/fetching_ticket_context.md` ← 3 refs — `Supported Git Platforms: GitHub, GitLab, Bitbucket`
- `docs/docs/core-abilities/interactivity.md` ← 6 refs — `Supported Git Platforms: GitHub, GitLab`
- `docs/docs/tools/add_docs.md` ← 3 refs — The `add_docs` tool scans the PR code changes and suggests documentation for any code components that are missing documentation, such as functions, classes, and…
- `docs/docs/tools/ask.md` ← 3 refs — The `ask` tool answers questions about the PR, based on the PR code changes. Make sure to be specific and clear in your questions.
- `docs/docs/tools/describe.md` ← 4 refs — The `describe` tool scans the PR code changes, and generates a description for the PR - title, type, summary, walkthrough and labels.
- `docs/docs/tools/generate_labels.md` ← 3 refs — The `generate_labels` tool scans the PR code changes and generates custom labels for the PR based on the content and context of the changes.
- `docs/docs/tools/help.md` ← 4 refs — The `help` tool provides a list of all the available tools and their descriptions.
- `docs/docs/tools/help_docs.md` ← 3 refs — The `help_docs` tool can answer a free-text question based on a git documentation folder.
- `docs/docs/tools/improve.md` ← 5 refs — The `improve` tool scans the PR code changes, and automatically generates meaningful suggestions for improving the PR code.
- `docs/docs/tools/review.md` ← 3 refs — The `review` tool scans the PR code changes, and generates feedback about the PR, aiming to aid the reviewing process.
- `docs/docs/tools/similar_issues.md` ← 3 refs — The similar issue tool retrieves the most similar issues to the current issue.
- `docs/docs/tools/update_changelog.md` ← 3 refs — The `update_changelog` tool automatically updates the CHANGELOG.md file with the PR changes.

### General Notes (37)
- `AGENTS.md` — **Do** match the interpreter requirement declared in `pyproject.toml` (Python ≥ 3.12) and install `requirements.txt` plus `requirements-dev.txt` before running …
- `README.md` — The Original Open-Source PR Reviewer
- `RELEASE_NOTES.md` — codiumai/pr-agent:0.11
- `codex.md` — This is a python project using fastapi.
- `docker/mosaico/README.md` — This directory holds the MOSAICO registration template for running pr-agent as a
- `docs/README.md`
- `docs/agents/domain.md` — How the engineering skills should consume this repo's domain documentation when exploring the codebase.
- `docs/agents/issue-tracker.md` — Issues for this repository live in the Linear project `pr-agent`.
- `docs/agents/triage-labels.md` — The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.
- `docs/docs/core-abilities/dynamic_context.md` ← 4 refs — `Supported Git Platforms: GitHub, GitLab, Bitbucket`
- `docs/docs/core-abilities/index.md` ← 3 refs — PR-Agent utilizes a variety of core abilities to provide a comprehensive and efficient code review experience. These abilities include:
- `docs/docs/core-abilities/metadata.md` ← 3 refs — `Supported Git Platforms: GitHub, GitLab, Bitbucket`
- `docs/docs/core-abilities/self_reflection.md` ← 3 refs — `Supported Git Platforms: GitHub, GitLab, Bitbucket`
- `docs/docs/faq/index.md` ← 2 refs — ??? note "Q: Can PR-Agent serve as a substitute for a human reviewer?"
- `docs/docs/index.md` ← 1 refs — [PR-Agent](https://github.com/the-pr-agent/pr-agent) is an open-source, AI-powered code review agent and a community-maintained legacy project of Qodo. It is di…
- `docs/docs/installation/azure.md` ← 2 refs — You can use a pre-built Action Docker image to run PR-Agent as an Azure DevOps pipeline.
- `docs/docs/installation/bitbucket.md` ← 2 refs — You can use the Bitbucket Pipeline system to run PR-Agent on every pull request open or update.
- `docs/docs/installation/gitea.md` ← 1 refs — In Gitea create a new user and give it "Reporter" role for the intended group or project.
- `docs/docs/installation/github.md` ← 2 refs — In this page we will cover how to install and run PR-Agent as a GitHub Action or GitHub App, and how to configure it for your needs.
- `docs/docs/installation/gitlab.md` ← 2 refs — You can use a pre-built Action Docker image to run PR-Agent as a GitLab pipeline. This is a simple way to get started with PR-Agent without setting up your own …
- _…and 17 more_

---
_Generated by [codesight](https://github.com/Houseofmvps/codesight) v1.18.0_