## Overview

The `review` tool scans the PR code changes, and generates feedback about the PR, aiming to aid the reviewing process.
<br>
The tool can be triggered automatically every time a new PR is [opened](../usage-guide/automations_and_usage.md#github-app-automatic-tools-when-a-new-pr-is-opened), or can be invoked manually by commenting on any PR:

```
/review
```

Note that the main purpose of the `review` tool is to provide the **PR reviewer** with useful feedback and insights. The PR author, in contrast, may prefer to save time and focus on the output of the [improve](./improve.md) tool, which provides actionable code suggestions.

(Read more about the different personas in the PR process and how PR-Agent aims to assist them in our [blog](https://www.codium.ai/blog/understanding-the-challenges-and-pain-points-of-the-pull-request-cycle/))

## Example usage

### Manual triggering

Invoke the tool manually by commenting `/review` on any PR:

![review comment](https://codium.ai/images/pr_agent/review_comment.png){width=512}

After ~30 seconds, the tool will generate a review for the PR:

![review](https://codium.ai/images/pr_agent/review3.png){width=512}

If you want to edit [configurations](#configuration-options), add the relevant ones to the command:

```
/review --pr_reviewer.some_config1=... --pr_reviewer.some_config2=...
```

### Automatic triggering

To run the `review` automatically when a PR is opened, define in a [configuration file](../usage-guide/configuration_options.md#wiki-configuration-file):

```
[github_app]
pr_commands = [
    "/review",
    ...
]

[pr_reviewer]
extra_instructions = "..."
...
```

- The `pr_commands` lists commands that will be executed automatically when a PR is opened.
- The `[pr_reviewer]` section contains the configurations for the `review` tool you want to edit (if any).

## Configuration options

### Council Review

Council Review runs several independent Review passes and asks a chair model to synthesize their structured results. It is **disabled by default**, so the `review` tool uses Standard Review unless an applicable settings layer enables it. A repository may opt in by adding this minimal section to its `.pr_agent.toml`:

```toml
[pr_council_review]
enabled = true
peer_evaluation = true
members = [
    { model = "provider/member-a", temperature = 0.2 },
    { model = "provider/member-b", reasoning_effort = "high" },
]
chair = { model = "provider/chair", temperature = 0.1, reasoning_effort = "medium" }
```

`members` must contain between 2 and 5 entries. Every member and the `chair` require a `model`. `temperature` and `reasoning_effort` are optional per-role inference overrides: temperature accepts values from 0 through 2, and reasoning effort accepts `none`, `minimal`, `low`, `medium`, `high`, or `xhigh`. Unsupported handler-level overrides are ignored with a sanitized notice. Set `peer_evaluation = false` to skip Peer Evaluation and send the independent member reviews directly to the chair.

Council-specific entries select models and their supported inference overrides only. Credentials continue to use the existing provider settings, environment variables, or `.secrets.toml`; AI timeouts inherit `config.ai_timeout`. The `[pr_council_review]` section follows the same [settings-layer precedence](../usage-guide/configuration_options.md#precedence) as other PR-Agent configuration: repository `.pr_agent.toml` values can override global defaults, while wiki and environment settings can override repository values.

Invalid enabled Council Review configuration produces a visible notice and falls back to Standard Review. A runtime Council Review failure does not publish a partial member response or silently rerun Standard Review.

#### Council Review prompts

Independent members use the existing Standard Review system and user prompts from `pr_agent/settings/pr_reviewer_prompts.toml`, so the normal `[pr_review_prompt]` overrides also apply to member reviews.

Peer Evaluation and chair synthesis use the overrideable `[pr_council_review_prompt]` section from `pr_agent/settings/pr_council_review_prompts.toml`:

- `peer_system` and `peer_user` rank anonymized structured member responses without the raw PR diff or model identities. `peer_user` receives `member_review_count` and `member_reviews`.
- `system` and `user` synthesize successful member reviews and available peer evaluations into the same structured YAML contract as Standard Review. `user` receives `member_review_count`, `member_reviews`, `peer_evaluation_count`, and `peer_evaluations`.

Override these prompt keys through the same settings layers as other prompts. Prompt rendering uses strict undefined-variable checks, so custom templates may reference only the variables available to their section.

#### Regression verification

The focused regression suite uses fake AI handlers and git providers; it does not call live models or require provider credentials:

```bash
PYTHONPATH=. uv run --python 3.12 --with-requirements requirements.txt --with-requirements requirements-dev.txt pytest tests/unittest/test_council_review.py -v
```

It covers Council Review configuration, execution stages, quorum and fallbacks, warnings, manual/automated/incremental Review modes, cancellation, and information-disclosure boundaries. Run the existing Standard Review and routing suites as part of the full unit suite before release.

???+ example "General options"

    <table>
      <tr>
        <td><b>persistent_comment</b></td>
        <td>If set to true, the review comment will be persistent, meaning that every new review request will edit the previous one. Default is true.</td>
      </tr>
      <tr>
      <td><b>final_update_message</b></td>
      <td>When set to true, updating a persistent review comment during online commenting will automatically add a short comment with a link to the updated review in the pull request .Default is true.</td>
      </tr>
      <tr>
        <td><b>extra_instructions</b></td>
        <td>Optional extra instructions to the tool. For example: "focus on the changes in the file X. Ignore change in ...".</td>
      </tr>
      <tr>
        <td><b>enable_help_text</b></td>
        <td>If set to true, the tool will display a help text in the comment. Default is false.</td>
      </tr>
      <tr>
        <td><b>num_max_findings</b></td>
        <td>Number of maximum returned findings. Default is 3.</td>
      </tr>
    </table>

???+ example "Enable\\disable specific sub-sections"

    <table>
      <tr>
        <td><b>require_score_review</b></td>
        <td>If set to true, the tool will add a section that scores the PR. Default is false.</td>
      </tr>
      <tr>
        <td><b>require_tests_review</b></td>
        <td>If set to true, the tool will add a section that checks if the PR contains tests. Default is true.</td>
      </tr>
      <tr>
        <td><b>require_estimate_effort_to_review</b></td>
        <td>If set to true, the tool will add a section that estimates the effort needed to review the PR. Default is true.</td>
      </tr>
      <tr>
        <td><b>require_estimate_contribution_time_cost</b></td>
        <td>If set to true, the tool will add a section that estimates the time required for a senior developer to create and submit such changes. Default is false.</td>
      </tr>
      <tr>
        <td><b>require_can_be_split_review</b></td>
        <td>If set to true, the tool will add a section that checks if the PR contains several themes, and can be split into smaller PRs. Default is false.</td>
      </tr>
      <tr>
        <td><b>require_security_review</b></td>
        <td>If set to true, the tool will add a section that checks if the PR contains a possible security or vulnerability issue. Default is true.</td>
      </tr>
        <tr>
        <td><b>require_todo_scan</b></td>
        <td>If set to true, the tool will add a section that lists TODO comments found in the PR code changes. Default is false.
        </td>
      </tr>
      <tr>
        <td><b>require_ticket_analysis_review</b></td>
        <td>If set to true, and the PR contains a GitHub or Jira ticket link, the tool will add a section that checks if the PR in fact fulfilled the ticket requirements. Default is true.</td>
      </tr>
    </table>

???+ example "Adding PR labels"

    You can enable\disable the `review` tool to add specific labels to the PR:

    <table>
      <tr>
        <td><b>enable_review_labels_security</b></td>
        <td>If set to true, the tool will publish a 'possible security issue' label if it detects a security issue. Default is true.</td>
      </tr>
      <tr>
        <td><b>enable_review_labels_effort</b></td>
        <td>If set to true, the tool will publish a 'Review effort x/5' label (1–5 scale). Default is true.</td>
      </tr>
    </table>

## Usage Tips

### General guidelines

!!! tip ""

    The `review` tool provides a collection of configurable feedbacks about a PR.
    It is recommended to review the [Configuration options](#configuration-options) section, and choose the relevant options for your use case.

    Some of the features that are disabled by default are quite useful, and should be considered for enabling. For example:
    `require_score_review`, and more.

    On the other hand, if you find one of the enabled features to be irrelevant for your use case, disable it. No default configuration can fit all use cases.

### Automation

!!! tip ""
    When you first install PR-Agent app, the [default mode](../usage-guide/automations_and_usage.md#github-app-automatic-tools-when-a-new-pr-is-opened) for the `review` tool is:
    ```
    pr_commands = ["/review", ...]
    ```
    Meaning the `review` tool will run automatically on every PR, without any additional configurations.
    Edit this field to enable/disable the tool, or to change the configurations used.

### Auto-generated PR labels by the Review Tool

!!! tip ""

    The `review` can tool automatically add labels to your Pull Requests:

    - **`possible security issue`**: This label is applied if the tool detects a potential [security vulnerability](https://github.com/the-pr-agent/pr-agent/blob/main/pr_agent/settings/pr_reviewer_prompts.toml#L134) in the PR's code. This feedback is controlled by the 'enable_review_labels_security' flag (default is true).
    - **`review effort [x/5]`**: This label estimates the [effort](https://github.com/the-pr-agent/pr-agent/blob/main/pr_agent/settings/pr_reviewer_prompts.toml#L118) required to review the PR on a relative scale of 1 to 5, where 'x' represents the assessed effort. This feedback is controlled by the 'enable_review_labels_effort' flag (default is true).
    - **`ticket compliance`**: Adds a label indicating code compliance level ("Fully compliant" | "PR Code Verified" | "Partially compliant" | "Not compliant") to any GitHub/Jira/Linea ticket linked in the PR. Controlled by the 'require_ticket_labels' flag (default: false). If 'require_no_ticket_labels' is also enabled, PRs without ticket links will receive a "No ticket found" label.


### Auto-blocking PRs from being merged based on the generated labels

!!! tip ""

    You can configure a CI/CD Action to prevent merging PRs with specific labels. For example, implement a dedicated [GitHub Action](https://medium.com/sequra-tech/quick-tip-block-pull-request-merge-using-labels-6cc326936221).

    This approach helps ensure PRs with potential security issues or ticket compliance problems will not be merged without further review.

    Since AI may make mistakes or lack complete context, use this feature judiciously. For flexibility, users with appropriate permissions can remove generated labels when necessary. When a label is removed, this action will be automatically documented in the PR discussion, clearly indicating it was a deliberate override by an authorized user to allow the merge.

### Extra instructions

!!! tip "" 

    Extra instructions are important.
    The `review` tool can be configured with extra instructions, which can be used to guide the model to a feedback tailored to the needs of your project.

    Be specific, clear, and concise in the instructions. With extra instructions, you are the prompter. Specify the relevant sub-tool, and the relevant aspects of the PR that you want to emphasize.

    Examples of extra instructions:
    ```
    [pr_reviewer]
    extra_instructions="""\
    In the code feedback section, emphasize the following:
    - Does the code logic cover relevant edge cases?
    - Is the code logic clear and easy to understand?
    - Is the code logic efficient?
    ...
    """
    ```
    Use triple quotes to write multi-line instructions. Use bullet points to make the instructions more readable.
