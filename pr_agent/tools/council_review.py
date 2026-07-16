from __future__ import annotations

import asyncio
import copy
import math
from dataclasses import dataclass, field
from typing import Any, Callable

import yaml
from jinja2 import Environment, StrictUndefined

from pr_agent.algo.ai_handlers.base_ai_handler import (
    BaseAiHandler,
    ModelInferenceSettings,
    UNSET,
)
from pr_agent.algo.pr_processing import get_pr_diff
from pr_agent.algo.token_handler import TokenHandler
from pr_agent.algo.utils import load_yaml
from pr_agent.config_loader import get_settings
from pr_agent.git_providers.git_provider import GitProvider
from pr_agent.log import get_logger

_ALLOWED_MODEL_CONFIG_KEYS = {"model", "temperature", "reasoning_effort"}
_ALLOWED_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh"}
_REVIEW_KEYS_FIX_YAML = [
    "ticket_compliance_check",
    "estimated_effort_to_review_[1-5]:",
    "security_concerns:",
    "key_issues_to_review:",
    "relevant_file:",
    "relevant_line:",
    "suggestion:",
]
_REVIEW_KEY_ORDER = [
    "ticket_compliance_check",
    "estimated_effort_to_review_[1-5]",
    "contribution_time_cost_estimate",
    "score",
    "relevant_tests",
    "insights_from_user_answers",
    "key_issues_to_review",
    "security_concerns",
    "todo_sections",
    "can_be_split",
]
_KEY_ISSUE_KEYS = {"relevant_file", "issue_header", "issue_content", "start_line", "end_line"}
_TICKET_COMPLIANCE_KEYS = {
    "ticket_url",
    "ticket_requirements",
    "fully_compliant_requirements",
    "not_compliant_requirements",
    "requires_further_human_verification",
}
_CONTRIBUTION_TIME_COST_KEYS = {"best_case", "average_case", "worst_case"}
_TODO_SECTION_KEYS = {"relevant_file", "line_number", "content"}
_SUB_PR_KEYS = {"relevant_files", "title"}


@dataclass(frozen=True)
class CouncilModelConfig:
    model: str
    inference_settings: ModelInferenceSettings = field(default_factory=ModelInferenceSettings)


@dataclass(frozen=True)
class CouncilReviewConfig:
    enabled: bool
    members: list[CouncilModelConfig] = field(default_factory=list)
    chair: CouncilModelConfig | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CouncilMemberReview:
    label: str
    model: str
    response: str
    parsed: dict[str, Any]
    metadata: dict[str, Any]
    source_diff: str


@dataclass(frozen=True)
class CouncilReviewResult:
    prediction: str
    metadata: dict[str, Any]


class CouncilReviewError(Exception):
    def __init__(self, public_message: str):
        super().__init__(public_message)
        self.public_message = public_message


def resolve_council_review_config() -> CouncilReviewConfig:
    """Return a valid enabled Council Review config or a disabled config with validation warnings."""
    section = get_settings().get("pr_council_review", None)
    if not section:
        return CouncilReviewConfig(enabled=False)
    if not hasattr(section, "get"):
        warning = "Invalid pr_council_review configuration; falling back to Standard Review: section must be a table"
        get_logger().warning(warning)
        return CouncilReviewConfig(enabled=False, warnings=[warning])

    warnings = []
    enabled = section.get("enabled", False)
    if enabled is False:
        return CouncilReviewConfig(enabled=False)
    if enabled is not True:
        warning = "Invalid pr_council_review configuration; falling back to Standard Review: enabled must be boolean"
        get_logger().warning(warning)
        return CouncilReviewConfig(enabled=False, warnings=[warning])

    try:
        members = [
            _parse_model_config(member, f"members[{index}]")
            for index, member in enumerate(section.get("members", []))
        ]
        chair = _parse_model_config(section.get("chair", {}), "chair")
        if not 2 <= len(members) <= 5:
            raise ValueError("pr_council_review.members must contain 2 to 5 entries")
        return CouncilReviewConfig(enabled=True, members=members, chair=chair)
    except (TypeError, ValueError) as exc:
        warning = f"Invalid pr_council_review configuration; falling back to Standard Review: {exc}"
        get_logger().warning(warning)
        warnings.append(warning)
        return CouncilReviewConfig(enabled=False, warnings=warnings)


def _parse_model_config(raw_config: Any, location: str) -> CouncilModelConfig:
    if not hasattr(raw_config, "get"):
        raise TypeError(f"{location} must be a table")
    unknown_keys = set(raw_config.keys()) - _ALLOWED_MODEL_CONFIG_KEYS
    if unknown_keys:
        raise ValueError(f"{location} contains unsupported keys: {sorted(unknown_keys)}")

    model = raw_config.get("model")
    if not isinstance(model, str) or not model.strip():
        raise ValueError(f"{location}.model must be a non-empty string")

    temperature = raw_config.get("temperature", UNSET)
    if temperature is not UNSET:
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            raise ValueError(f"{location}.temperature must be numeric")
        temperature = float(temperature)
        if not math.isfinite(temperature):
            raise ValueError(f"{location}.temperature must be finite")
        if not 0 <= temperature <= 2:
            raise ValueError(f"{location}.temperature must be between 0 and 2")

    reasoning_effort = raw_config.get("reasoning_effort", UNSET)
    if reasoning_effort is not UNSET:
        if not isinstance(reasoning_effort, str) or reasoning_effort not in _ALLOWED_REASONING_EFFORTS:
            raise ValueError(f"{location}.reasoning_effort must be one of {sorted(_ALLOWED_REASONING_EFFORTS)}")

    return CouncilModelConfig(
        model=model.strip(),
        inference_settings=ModelInferenceSettings(temperature=temperature, reasoning_effort=reasoning_effort),
    )


class CouncilReviewRunner:
    """Runs Council Review and returns the structured Review prediction to PRReviewer."""

    def __init__(
        self,
        *,
        config: CouncilReviewConfig,
        git_provider: GitProvider,
        token_handler: TokenHandler,
        vars: dict[str, Any],
        ai_handler_factory: Callable[[], BaseAiHandler],
        main_language: str,
    ):
        self.config = config
        self.git_provider = git_provider
        self.token_handler = token_handler
        self.vars = vars
        self.ai_handler_factory = ai_handler_factory
        self.main_language = main_language

    async def run(self) -> CouncilReviewResult:
        member_results = await asyncio.gather(
            *(self._run_member(member, index) for index, member in enumerate(self.config.members, start=1)),
            return_exceptions=True,
        )
        successful_reviews = []
        failed_members = 0
        for result in member_results:
            if isinstance(result, Exception):
                failed_members += 1
                get_logger().warning("Council member review failed", artifact={"error": str(result)})
            else:
                successful_reviews.append(result)

        if len(successful_reviews) < 2:
            raise CouncilReviewError("Council Review failed because fewer than two members returned parseable reviews.")

        chair_response, chair_metadata = await self._run_chair(successful_reviews)
        metadata = {
            "strategy": "council_review",
            "member_count": len(self.config.members),
            "successful_member_count": len(successful_reviews),
            "failed_member_count": failed_members,
            "chair_model": self.config.chair.model,
            "warnings": chair_metadata.get("warnings", []),
        }
        return CouncilReviewResult(prediction=chair_response, metadata=metadata)

    async def _run_member(self, member: CouncilModelConfig, index: int) -> CouncilMemberReview:
        patches_diff = get_pr_diff(
            self.git_provider,
            self.token_handler,
            member.model,
            add_line_numbers_to_hunks=True,
            disable_extra_lines=False,
        )
        if not patches_diff:
            raise CouncilReviewError(f"Council member {index} received an empty diff")

        variables = copy.deepcopy(self.vars)
        variables["diff"] = patches_diff
        system_prompt = _render_prompt(get_settings().pr_review_prompt.system, variables)
        user_prompt = _render_prompt(get_settings().pr_review_prompt.user, variables)
        handler = self._new_handler()
        result = await handler.chat_completion_with_metadata(
            model=member.model,
            system=system_prompt,
            user=user_prompt,
            inference_settings=member.inference_settings,
        )
        parsed = _parse_review_prediction(result.response, variables)
        return CouncilMemberReview(
            label=f"member_{index}",
            model=member.model,
            response=result.response,
            parsed=parsed,
            metadata=result.metadata,
            source_diff=patches_diff,
        )

    async def _run_chair(self, member_reviews: list[CouncilMemberReview]) -> tuple[str, dict[str, Any]]:
        variables = copy.deepcopy(self.vars)
        variables.update({
            "member_reviews": _format_member_reviews(member_reviews),
            "member_review_count": len(member_reviews),
        })
        variables.pop("diff", None)
        system_prompt = _render_prompt(get_settings().pr_council_review_prompt.system, variables)
        user_prompt = _render_prompt(get_settings().pr_council_review_prompt.user, variables)
        handler = self._new_handler()
        result = await handler.chat_completion_with_metadata(
            model=self.config.chair.model,
            system=system_prompt,
            user=user_prompt,
            inference_settings=self.config.chair.inference_settings,
        )
        _parse_review_prediction(result.response, variables)
        return result.response, result.metadata

    def _new_handler(self) -> BaseAiHandler:
        handler = self.ai_handler_factory()
        handler.main_pr_language = self.main_language
        return handler


def _render_prompt(template: str, variables: dict[str, Any]) -> str:
    return Environment(undefined=StrictUndefined).from_string(template).render(variables)


def _parse_review_prediction(response: str, variables: dict[str, Any]) -> dict[str, Any]:
    data = load_yaml(
        response.strip(),
        keys_fix_yaml=_REVIEW_KEYS_FIX_YAML,
        first_key="review",
        last_key="security_concerns",
    )
    if not isinstance(data, dict) or not isinstance(data.get("review"), dict):
        raise CouncilReviewError("Council participant returned an unparseable structured Review result")

    return {"review": _validate_and_project_review(data["review"], variables)}


def _validate_and_project_review(review: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    required_keys = {"key_issues_to_review"}
    if variables.get("related_tickets"):
        required_keys.add("ticket_compliance_check")
    if variables.get("require_estimate_effort_to_review", False):
        required_keys.add("estimated_effort_to_review_[1-5]")
    if variables.get("require_estimate_contribution_time_cost", False):
        required_keys.add("contribution_time_cost_estimate")
    if variables.get("require_score", False):
        required_keys.add("score")
    if variables.get("require_tests", False):
        required_keys.add("relevant_tests")
    if variables.get("question_str"):
        required_keys.add("insights_from_user_answers")
    if variables.get("require_security_review", False):
        required_keys.add("security_concerns")
    if variables.get("require_todo_scan", False):
        required_keys.add("todo_sections")
    if variables.get("require_can_be_split_review", False):
        required_keys.add("can_be_split")

    allowed_keys = set(_REVIEW_KEY_ORDER)
    if unknown_keys := set(review) - allowed_keys:
        raise CouncilReviewError(
            f"Council participant returned unsupported structured Review keys: {sorted(unknown_keys)}"
        )
    if missing_keys := required_keys - set(review):
        raise CouncilReviewError(
            f"Council participant omitted required structured Review keys: {sorted(missing_keys)}"
        )

    projected_review = {}
    for key in _REVIEW_KEY_ORDER:
        if key in review:
            projected_review[key] = _validate_review_value(key, review[key])
    return projected_review


def _validate_review_value(key: str, value: Any) -> Any:
    if key == "key_issues_to_review":
        _validate_list_of_dicts(value, _KEY_ISSUE_KEYS, key)
    elif key == "ticket_compliance_check":
        _validate_list_of_dicts(value, _TICKET_COMPLIANCE_KEYS, key)
    elif key == "contribution_time_cost_estimate":
        _validate_dict(value, _CONTRIBUTION_TIME_COST_KEYS, key)
    elif key == "todo_sections":
        if isinstance(value, str):
            return value
        _validate_list_of_dicts(value, _TODO_SECTION_KEYS, key)
    elif key == "can_be_split":
        _validate_list_of_dicts(value, _SUB_PR_KEYS, key)
        for item in value:
            relevant_files = item["relevant_files"]
            if not isinstance(relevant_files, list) or not all(isinstance(file, str) for file in relevant_files):
                raise CouncilReviewError("Council participant returned an invalid structured Review result")
    elif key in {"relevant_tests", "security_concerns"}:
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if not isinstance(value, str):
            raise CouncilReviewError("Council participant returned an invalid structured Review result")
    elif key == "insights_from_user_answers":
        if not isinstance(value, str):
            raise CouncilReviewError("Council participant returned an invalid structured Review result")
    elif key == "score":
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise CouncilReviewError("Council participant returned an invalid structured Review result")
        try:
            score = int(value)
        except ValueError as exc:
            raise CouncilReviewError("Council participant returned an invalid structured Review result") from exc
        if not 0 <= score <= 100:
            raise CouncilReviewError("Council participant returned an invalid structured Review result")
        return str(value)
    elif key == "estimated_effort_to_review_[1-5]":
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise CouncilReviewError("Council participant returned an invalid structured Review result")
        try:
            effort = int(value)
        except ValueError as exc:
            raise CouncilReviewError("Council participant returned an invalid structured Review result") from exc
        if not 1 <= effort <= 5:
            raise CouncilReviewError("Council participant returned an invalid structured Review result")
        return effort
    return value


def _validate_list_of_dicts(value: Any, expected_keys: set[str], location: str) -> None:
    if not isinstance(value, list):
        raise CouncilReviewError("Council participant returned an invalid structured Review result")
    for item in value:
        _validate_dict(item, expected_keys, location)


def _validate_dict(value: Any, expected_keys: set[str], location: str) -> None:
    if not isinstance(value, dict):
        raise CouncilReviewError("Council participant returned an invalid structured Review result")
    if set(value) != expected_keys:
        raise CouncilReviewError(f"Council participant returned invalid structured Review fields for {location}")
    for item_value in value.values():
        if not isinstance(item_value, (int, str, list)):
            raise CouncilReviewError("Council participant returned an invalid structured Review result")


def _format_member_reviews(member_reviews: list[CouncilMemberReview]) -> str:
    rendered_reviews = []
    for index, review in enumerate(member_reviews, start=1):
        normalized_review = yaml.safe_dump(review.parsed, sort_keys=False)
        redacted_review = _redact_diff_content(normalized_review, review.source_diff)
        rendered_reviews.append(f"Member Review {index}:\n```yaml\n{redacted_review.strip()}\n```")
    return "\n\n".join(rendered_reviews)


def _redact_diff_content(review_text: str, source_diff: str) -> str:
    if not source_diff:
        return review_text

    redacted_text = review_text.replace(source_diff, "[redacted raw diff]")
    for line in source_diff.splitlines():
        stripped_line = line.strip()
        diff_payload = stripped_line.lstrip("+- ")
        for sensitive_text in {stripped_line, diff_payload}:
            if len(sensitive_text) >= 3:
                redacted_text = redacted_text.replace(sensitive_text, "[redacted diff line]")
    return redacted_text
