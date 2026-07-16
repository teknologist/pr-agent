# Council Review Specification

Status: Agreed — grilling complete

## Goal

Add an optional Council Review strategy to PR-Agent. When enabled, existing Review commands use multiple independent model reviews, optional peer evaluation, and chair synthesis while preserving the existing `/review` output and publishing contract.

Domain terms are defined in [`../../CONTEXT.md`](../../CONTEXT.md).

## User-facing boundary

- Council Review is a Review strategy, not a new slash command.
- When enabled, it applies to manual and automated Reviews (`/review`, `/review_pr`, and `/auto_review`).
- `/answer` is unaffected.
- Incremental Review (`/review -i`) is supported and uses the existing incremental scope and gates.
- Successful output retains the Standard Review format and publishing behavior.
- A successful Council Review includes a brief strategy attribution, without model identities or deliberation details.

## Workflow

### Stage 1: Independent member reviews

- Configure at least 2 and at most 5 Council Members.
- Members run independently and concurrently.
- Repeated model identities are allowed.
- Each member receives PR evidence prepared with PR-Agent's existing model-specific diff/token logic.
- Each member must produce a parseable existing structured Review result; malformed or incomplete output is a failed member result.
- At least 2 member reviews must succeed to establish Council Quorum.
- If Council Quorum is not reached, Council Review fails without Standard Review fallback or publication of a lone member result.
- Council Members use exactly their configured models; global fallback models do not replace failed members.

### Stage 2: Peer Evaluation

- Peer Evaluation is configurable and enabled by default.
- When enabled, the configured Council Members evaluate the successful member reviews concurrently.
- Reviews are anonymized as response labels during Peer Evaluation.
- Peer Evaluation is best effort. Partial or total failure does not block synthesis after Council Quorum is reached.
- Peer evaluators receive member reviews, not the raw PR diff.

### Stage 3: Chair synthesis

- The Council Chair receives successful member reviews and available peer evaluations, but not the raw PR diff.
- The chair must produce the same structured result expected by Standard Review.
- If the configured chair fails, existing global `config.fallback_models` are tried in order as fallback chairs.
- Chair-specific temperature and reasoning-effort settings also apply to fallback-chair attempts when supported.

## Chair-failure Member Fallback

If the configured chair and all global fallback chairs fail:

1. Member Fallback is available only when Peer Evaluation produced at least 2 valid complete rankings.
2. A ranking is valid only if it contains every successful member response exactly once and contains no unknown labels.
3. Valid rankings are aggregated with Borda count.
4. The highest-scoring member Review becomes the final Review.
5. A top-score tie is resolved by configured member order.
6. If ranking evidence is unavailable or insufficient, no Review is published.

## Configuration

Council orchestration uses a dedicated section:

```toml
[pr_council_review]
enabled = false
peer_evaluation = true

members = [
  { model = "provider/model-a", temperature = 0.2, reasoning_effort = "high" },
  { model = "provider/model-b", temperature = 0.1, reasoning_effort = "medium" },
]

chair = { model = "provider/model-c", temperature = 0.1, reasoning_effort = "high" }
```

Rules:

- An absent section or `enabled = false` selects Standard Review.
- `members` contains 2–5 entries when enabled.
- Each member and the `chair` entry has a model plus optional `temperature` and `reasoning_effort` overrides.
- Omitted inference overrides inherit existing global settings.
- Credentials and provider secrets remain in PR-Agent's existing settings and `.secrets.toml`; Council Review does not duplicate them.
- Global timeouts, publishing settings, and provider configuration remain authoritative.
- The section participates in all normal PR-Agent settings layers, including deployment settings, environment/extra configuration, and repository `.pr_agent.toml`.

## Degradation and warnings

- Invalid enabled council configuration falls back to Standard Review.
- That fallback is reported in service logs and as a concise note in the published Review.
- If an active AI handler does not support a configured per-model override, Council Review continues without that override.
- Ignored overrides are reported in service logs and as a concise note in the published Review.
- If normal no-findings policy suppresses the Review, a required council degradation warning is published as a standalone concise comment instead.
- Provider-level retries remain available; model-identity switching follows only the explicit member/chair rules above.
- Terminal runtime failures, including quorum failure or exhausted chair/Member Fallback paths, do not trigger Standard Review.
- Terminal failures emit structured logs and a concise PR comment without raw model errors, model topology, or deliberation content.

## Prompt ownership

- Council Member reviews reuse the existing `[pr_review_prompt]` templates and structured output contract.
- Peer Evaluation and chair synthesis use built-in templates from a new `[pr_council_review_prompt]` settings section.
- The new prompt section is loaded through existing Dynaconf settings and may be overridden through `.pr_agent.toml` like other PR-Agent prompts.
- Long prompt templates are not embedded in the orchestration section.

## Execution and cancellation

- Independent review and Peer Evaluation calls run concurrently within their respective stages.
- A stage waits for every configured call to succeed, fail, or reach the existing PR-Agent per-call timeout before evaluating quorum or continuing.
- Existing provider retry behavior remains authoritative.
- Cancelling the Review request cancels all outstanding council tasks.

## Observability

Council Review emits structured metadata for strategy, stage, role/model, duration, success or failure, token usage when available, quorum, and fallback decisions. It does not add raw member reviews, peer evaluations, rankings, or chair output to logs.

## Module boundary

- `PRReviewer` remains responsible for Review scope, ticket extraction, incremental gating, formatting, labels, comments, and publication.
- A dedicated council runner module owns configuration validation, per-model prediction calls, concurrent stages, quorum, ranking, chair fallbacks, Member Fallback, attribution, and warnings.
- The runner returns a final structured Review prediction and metadata to `PRReviewer`; it does not publish directly.

## Verification

Completion requires deterministic tests with fake AI handlers/providers covering configuration validation, parallel stages, quorum, ranking validation and Borda aggregation, chair/model fallbacks, warning visibility, structured output, incremental scope, cancellation, and existing Standard Review regressions. Live-model testing is optional and not required.

## Information disclosure

A normal successful Review does not publish:

- Council Member or Chair model identifiers;
- raw member reviews;
- peer-evaluation text;
- rankings, Borda scores, or voting details.

## Open questions

None. The design was confirmed after the grilling session. Implementation remains separately authorized work.
