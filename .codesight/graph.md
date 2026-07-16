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
