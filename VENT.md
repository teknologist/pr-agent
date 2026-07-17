# VENT

Feedback log. Repeated/systemic workflow friction that should become future automation, docs, or workflow fixes.

## 26-07-16 15:51 — process-login-ssh-add-hang

Two process-managed commands (vet and full verification) repeatedly hung before execution because process uses `bash -lc`, whose login profile launched interactive `ssh-add`; child inspection showed only ssh-add running and logs stayed empty. Workaround: terminate processes and rerun verification with structured_return/direct bash. Prevent by making process startup non-interactive or bypassing login-shell ssh-add hooks.
## 26-07-16 16:31 — vet process hangs

During PYTTECH-7622 ReviewMerge, two vet invocations ran for over five minutes with zero stdout/stderr and had to be terminated. The repeated workaround was manual focused diff review plus deterministic pytest/flake8 verification. Vet should emit heartbeat/progress or fail with an actionable timeout/auth error so agents can distinguish slow review from a hung provider.
## 26-07-16 18:43 — review tooling and background verification

ReviewMerge hit repeated avoidable tool failures: both vet passes failed because `vet` was not installed, llm_council failed because its required workflow backend was unavailable, and process-based verification hung because the process wrapper launches a login shell whose profile blocks in ssh-add. Workarounds were a direct adversarial review plus review_loop and `structured_return` for the exact verification command. Prevent this by preflighting reviewer backends/CLI availability and running managed processes without interactive login-shell startup.
