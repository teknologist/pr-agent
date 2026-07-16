from __future__ import annotations

import asyncio
import copy
import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable

import yaml
from jinja2 import Environment, StrictUndefined

from pr_agent.algo.ai_handlers.base_ai_handler import (
    BaseAiHandler,
    ModelInferenceSettings,
    UNSET,
)
from pr_agent.algo.pr_processing import _get_all_deployments, get_pr_diff
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
_KEY_ISSUE_SCHEMA = {
    "relevant_file": str,
    "issue_header": str,
    "issue_content": str,
    "start_line": int,
    "end_line": int,
}
_TICKET_COMPLIANCE_SCHEMA = {
    "ticket_url": str,
    "ticket_requirements": str,
    "fully_compliant_requirements": str,
    "not_compliant_requirements": str,
    "requires_further_human_verification": str,
}
_CONTRIBUTION_TIME_COST_SCHEMA = {"best_case": str, "average_case": str, "worst_case": str}
_TODO_SECTION_SCHEMA = {"relevant_file": str, "line_number": int, "content": str}
_SUB_PR_SCHEMA = {"relevant_files": list, "title": str}
_NUMBERED_DIFF_LINE = re.compile(r"^\d+\s+[ +\-](.*)$")
_MAX_COUNCIL_FAN_OUT = 5
_TOKEN_USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens", "input_tokens", "output_tokens")


@dataclass(frozen=True)
class CouncilModelConfig:
    model: str
    inference_settings: ModelInferenceSettings = field(default_factory=ModelInferenceSettings)


@dataclass(frozen=True)
class CouncilReviewConfig:
    enabled: bool
    members: list[CouncilModelConfig] = field(default_factory=list)
    chair: CouncilModelConfig | None = None
    peer_evaluation: bool = True
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
class CouncilPeerEvaluation:
    evaluator_label: str
    response: str
    parsed: dict[str, Any]
    metadata: dict[str, Any]


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
        peer_evaluation = section.get("peer_evaluation", True)
        if not isinstance(peer_evaluation, bool):
            raise ValueError("pr_council_review.peer_evaluation must be boolean")
        if not 2 <= len(members) <= 5:
            raise ValueError("pr_council_review.members must contain 2 to 5 entries")
        return CouncilReviewConfig(
            enabled=True,
            members=members,
            chair=chair,
            peer_evaluation=peer_evaluation,
        )
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
        self.ai_handler = self._new_handler()
        self.call_metadata: list[dict[str, Any]] = []

    async def run(self) -> CouncilReviewResult:
        member_results = await self._run_stage([
            self._run_member(member, index) for index, member in enumerate(self.config.members, start=1)
        ])
        successful_reviews = []
        failed_members = 0
        for result in member_results:
            if isinstance(result, BaseException):
                failed_members += 1
                get_logger().warning("Council member review failed")
            else:
                successful_reviews.append(result)

        quorum = {"required": 2, "successful": len(successful_reviews), "met": len(successful_reviews) >= 2}
        get_logger().info(
            "Council Review quorum evaluated",
            artifact={"strategy": "council_review", "stage": "independent_review", "quorum": quorum},
        )
        if not quorum["met"]:
            self._log_terminal_fallback_decision(
                quorum,
                chair_fallback="not_evaluated",
                member_fallback="not_evaluated",
            )
            raise CouncilReviewError("Council Review failed because fewer than two members returned parseable reviews.")

        peer_evaluations = []
        failed_peer_evaluations = 0
        if self.config.peer_evaluation:
            peer_results = await self._run_stage([
                self._run_peer_evaluation(member, index, successful_reviews)
                for index, member in enumerate(self.config.members, start=1)
            ])
            for result in peer_results:
                if isinstance(result, BaseException):
                    failed_peer_evaluations += 1
                    get_logger().warning("Council peer evaluation failed")
                else:
                    peer_evaluations.append(result)

        chair_response = None
        chair_metadata = {}
        chair_model = None
        chair_models = [self.config.chair.model, *_get_fallback_models()]
        original_deployment_id = get_settings().get("openai.deployment_id", None)
        try:
            chair_attempts = zip(chair_models, _get_all_deployments(chair_models))
            for model, deployment_id in chair_attempts:
                try:
                    get_settings().set("openai.deployment_id", deployment_id)
                    chair_response, chair_metadata = await self._run_chair(
                        model,
                        successful_reviews,
                        peer_evaluations,
                    )
                    chair_model = model
                    break
                except Exception:
                    get_logger().warning(
                        "Council chair synthesis failed",
                        artifact={"model": model},
                    )
        except Exception as exc:
            get_logger().warning("Council chair fallback configuration failed")
            self._log_terminal_fallback_decision(
                quorum,
                chair_fallback="configuration_error",
                member_fallback="not_evaluated",
            )
            raise CouncilReviewError("Council Review failed during chair synthesis.") from exc
        finally:
            get_settings().set("openai.deployment_id", original_deployment_id)

        synthesis_strategy = "chair"
        if chair_response is None:
            member_fallback = _select_member_fallback(successful_reviews, peer_evaluations)
            if member_fallback is None:
                self._log_terminal_fallback_decision(
                    quorum,
                    chair_fallback="exhausted" if len(chair_models) > 1 else "not_configured",
                    member_fallback="unavailable",
                )
                raise CouncilReviewError("Council Review failed during chair synthesis.")
            chair_response = yaml.safe_dump(member_fallback.parsed, sort_keys=False)
            chair_model = None
            synthesis_strategy = "member_fallback"

        if chair_model == self.config.chair.model:
            chair_fallback_decision = "not_used"
        elif chair_model is not None:
            chair_fallback_decision = "used"
        elif len(chair_models) > 1:
            chair_fallback_decision = "exhausted"
        else:
            chair_fallback_decision = "not_configured"

        metadata = {
            "strategy": "council_review",
            "member_count": len(self.config.members),
            "successful_member_count": len(successful_reviews),
            "failed_member_count": failed_members,
            "quorum": quorum,
            "peer_evaluation_enabled": self.config.peer_evaluation,
            "successful_peer_evaluation_count": len(peer_evaluations),
            "failed_peer_evaluation_count": failed_peer_evaluations,
            "chair_model": chair_model,
            "synthesis_strategy": synthesis_strategy,
            "fallback_decisions": {
                "standard_review": "not_used",
                "chair_fallback": chair_fallback_decision,
                "member_fallback": "used" if synthesis_strategy == "member_fallback" else "not_used",
            },
            "calls": list(self.call_metadata),
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
        result, parsed = await self._complete_call(
            stage="independent_review",
            role="member",
            participant=member,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            parse_response=lambda response: _parse_review_prediction(response, variables),
        )
        return CouncilMemberReview(
            label=f"response_{index}",
            model=member.model,
            response=result.response,
            parsed=parsed,
            metadata=result.metadata,
            source_diff=patches_diff,
        )

    async def _run_peer_evaluation(
        self,
        member: CouncilModelConfig,
        index: int,
        member_reviews: list[CouncilMemberReview],
    ) -> CouncilPeerEvaluation:
        variables = copy.deepcopy(self.vars)
        variables.update({
            "member_reviews": _format_member_reviews(member_reviews),
            "member_review_count": len(member_reviews),
        })
        variables.pop("diff", None)
        system_prompt = _render_prompt(get_settings().pr_council_review_prompt.peer_system, variables)
        user_prompt = _render_prompt(get_settings().pr_council_review_prompt.peer_user, variables)
        expected_labels = [review.label for review in member_reviews]
        result, parsed = await self._complete_call(
            stage="peer_evaluation",
            role="peer",
            participant=member,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            parse_response=lambda response: _parse_peer_evaluation(response, expected_labels),
        )
        return CouncilPeerEvaluation(
            evaluator_label=f"evaluator_{index}",
            response=result.response,
            parsed=parsed,
            metadata=result.metadata,
        )

    async def _run_chair(
        self,
        model: str,
        member_reviews: list[CouncilMemberReview],
        peer_evaluations: list[CouncilPeerEvaluation],
    ) -> tuple[str, dict[str, Any]]:
        variables = copy.deepcopy(self.vars)
        variables.update({
            "member_reviews": _format_member_reviews(member_reviews),
            "member_review_count": len(member_reviews),
            "peer_evaluations": _format_peer_evaluations(peer_evaluations),
            "peer_evaluation_count": len(peer_evaluations),
        })
        variables.pop("diff", None)
        system_prompt = _render_prompt(get_settings().pr_council_review_prompt.system, variables)
        user_prompt = _render_prompt(get_settings().pr_council_review_prompt.user, variables)
        participant = CouncilModelConfig(model=model, inference_settings=self.config.chair.inference_settings)
        result, parsed = await self._complete_call(
            stage="chair_synthesis",
            role="chair",
            participant=participant,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            parse_response=lambda response: _parse_review_prediction(response, variables),
        )
        return yaml.safe_dump(parsed, sort_keys=False), result.metadata

    async def _run_stage(self, operations: list[Any]) -> list[Any]:
        if len(operations) > _MAX_COUNCIL_FAN_OUT:
            for operation in operations:
                operation.close()
            raise CouncilReviewError("Council Review stage exceeds the five-member fan-out limit.")

        tasks = [asyncio.create_task(operation) for operation in operations]
        try:
            return await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    async def _complete_call(
        self,
        *,
        stage: str,
        role: str,
        participant: CouncilModelConfig,
        system_prompt: str,
        user_prompt: str,
        parse_response: Callable[[str], Any],
    ) -> tuple[Any, Any]:
        started_at = asyncio.get_running_loop().time()
        result = None
        token_usage = None
        try:
            completion = self.ai_handler.chat_completion_with_metadata(
                model=participant.model,
                system=system_prompt,
                user=user_prompt,
                inference_settings=participant.inference_settings,
            )
            if getattr(self.ai_handler, "manages_ai_timeout", False):
                result = await completion
            else:
                result = await asyncio.wait_for(completion, timeout=get_settings().config.ai_timeout)
            result_metadata = result.metadata or {}
            token_usage = _normalize_token_usage(result_metadata.get("token_usage", result_metadata.get("usage")))
            parsed = parse_response(result.response)
        except asyncio.TimeoutError:
            self._record_call(stage, role, participant.model, started_at, "timeout", token_usage)
            raise
        except asyncio.CancelledError:
            self._record_call(stage, role, participant.model, started_at, "cancelled", token_usage)
            raise
        except BaseException:
            self._record_call(stage, role, participant.model, started_at, "failure", token_usage)
            raise

        self._record_call(stage, role, participant.model, started_at, "success", token_usage)
        return result, parsed

    def _record_call(
        self,
        stage: str,
        role: str,
        model: str,
        started_at: float,
        outcome: str,
        token_usage: Any = None,
    ) -> None:
        metadata = {
            "strategy": "council_review",
            "stage": stage,
            "role": role,
            "model": model,
            "duration_ms": round((asyncio.get_running_loop().time() - started_at) * 1000, 3),
            "outcome": outcome,
        }
        if token_usage is not None:
            metadata["token_usage"] = token_usage
        self.call_metadata.append(metadata)
        get_logger().info("Council Review call completed", artifact=metadata)

    @staticmethod
    def _log_terminal_fallback_decision(
        quorum: dict[str, Any],
        *,
        chair_fallback: str,
        member_fallback: str,
    ) -> None:
        get_logger().info(
            "Council Review fallback evaluated",
            artifact={
                "strategy": "council_review",
                "stage": "chair_synthesis",
                "quorum": quorum,
                "fallback_decisions": {
                    "standard_review": "not_used",
                    "chair_fallback": chair_fallback,
                    "member_fallback": member_fallback,
                },
            },
        )

    def _new_handler(self) -> BaseAiHandler:
        handler = self.ai_handler_factory()
        handler.main_pr_language = self.main_language
        enable_redaction = getattr(handler, "enable_council_redaction", None)
        if callable(enable_redaction):
            redaction_enabled = enable_redaction()
        else:
            redaction_enabled = getattr(handler, "supports_council_redaction", False)
            handler.suppress_raw_logging = redaction_enabled
        if not redaction_enabled:
            raise CouncilReviewError("Council Review requires an AI handler with raw-output redaction support.")
        return handler


def _normalize_token_usage(raw_usage: Any) -> dict[str, int] | None:
    if raw_usage is None:
        return None

    token_usage = {}
    for field_name in _TOKEN_USAGE_FIELDS:
        value = raw_usage.get(field_name) if isinstance(raw_usage, dict) else getattr(raw_usage, field_name, None)
        if isinstance(value, int) and not isinstance(value, bool):
            token_usage[field_name] = value
    return token_usage or None


def _get_fallback_models() -> list[str]:
    fallback_models = get_settings().config.fallback_models
    if isinstance(fallback_models, str):
        fallback_models = fallback_models.split(",")
    return [model.strip() for model in fallback_models if isinstance(model, str) and model.strip()]


def _select_member_fallback(
    member_reviews: list[CouncilMemberReview],
    peer_evaluations: list[CouncilPeerEvaluation],
) -> CouncilMemberReview | None:
    if len(peer_evaluations) < 2:
        return None

    scores = {review.label: 0 for review in member_reviews}
    for evaluation in peer_evaluations:
        ranking = evaluation.parsed["peer_evaluation"]["ranking"]
        if len(ranking) != len(scores) or set(ranking) != set(scores):
            return None
        for points, label in enumerate(reversed(ranking)):
            scores[label] += points

    return max(member_reviews, key=lambda review: scores[review.label], default=None)


def _render_prompt(template: str, variables: dict[str, Any]) -> str:
    return Environment(undefined=StrictUndefined).from_string(template).render(variables)


def _parse_review_prediction(response: str, variables: dict[str, Any]) -> dict[str, Any]:
    data = load_yaml(
        response.strip(),
        keys_fix_yaml=_REVIEW_KEYS_FIX_YAML,
        first_key="review",
        last_key="security_concerns",
        suppress_raw_logging=True,
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
        return _validate_list_of_dicts(value, _KEY_ISSUE_SCHEMA, key)
    if key == "ticket_compliance_check":
        return _validate_list_of_dicts(value, _TICKET_COMPLIANCE_SCHEMA, key)
    if key == "contribution_time_cost_estimate":
        return _validate_dict(value, _CONTRIBUTION_TIME_COST_SCHEMA, key)
    if key == "todo_sections":
        if isinstance(value, str):
            return value
        return _validate_list_of_dicts(value, _TODO_SECTION_SCHEMA, key)
    if key == "can_be_split":
        return _validate_list_of_dicts(value, _SUB_PR_SCHEMA, key)
    if key in {"relevant_tests", "security_concerns"}:
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


def _validate_list_of_dicts(
    value: Any,
    schema: dict[str, type],
    location: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise CouncilReviewError("Council participant returned an invalid structured Review result")
    return [_validate_dict(item, schema, location) for item in value]


def _validate_dict(value: Any, schema: dict[str, type], location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CouncilReviewError("Council participant returned an invalid structured Review result")
    if set(value) != set(schema):
        raise CouncilReviewError(f"Council participant returned invalid structured Review fields for {location}")

    normalized = {}
    for field_name, expected_type in schema.items():
        field_value = value[field_name]
        if expected_type is int:
            if isinstance(field_value, bool) or not isinstance(field_value, (int, str)):
                raise CouncilReviewError("Council participant returned an invalid structured Review result")
            try:
                field_value = int(field_value)
            except ValueError as exc:
                raise CouncilReviewError("Council participant returned an invalid structured Review result") from exc
        elif expected_type is list:
            if not isinstance(field_value, list) or not all(isinstance(item, str) for item in field_value):
                raise CouncilReviewError("Council participant returned an invalid structured Review result")
        elif not isinstance(field_value, expected_type):
            raise CouncilReviewError("Council participant returned an invalid structured Review result")
        normalized[field_name] = field_value
    return normalized


def _parse_peer_evaluation(response: str, expected_labels: list[str]) -> dict[str, Any]:
    try:
        data = yaml.safe_load(response.strip())
    except yaml.YAMLError as exc:
        raise CouncilReviewError("Council peer evaluator returned an unparseable result") from exc
    if not isinstance(data, dict) or not isinstance(data.get("peer_evaluation"), dict):
        raise CouncilReviewError("Council peer evaluator returned an unparseable result")

    evaluation = data["peer_evaluation"]
    ranking = evaluation.get("ranking")
    rationale = evaluation.get("rationale")
    if (
        not isinstance(ranking, list)
        or not all(isinstance(label, str) for label in ranking)
        or len(ranking) != len(expected_labels)
        or set(ranking) != set(expected_labels)
    ):
        raise CouncilReviewError("Council peer evaluator returned an invalid ranking")
    if not isinstance(rationale, str):
        raise CouncilReviewError("Council peer evaluator returned an invalid rationale")
    return {"peer_evaluation": {"ranking": ranking, "rationale": rationale}}


def _format_member_reviews(member_reviews: list[CouncilMemberReview]) -> str:
    rendered_reviews = []
    for review in member_reviews:
        redacted_review = _redact_review_data(review.parsed, review.source_diff)
        normalized_review = yaml.safe_dump(redacted_review, sort_keys=False)
        rendered_reviews.append(f"{review.label}:\n```yaml\n{normalized_review.strip()}\n```")
    return "\n\n".join(rendered_reviews)


def _format_peer_evaluations(peer_evaluations: list[CouncilPeerEvaluation]) -> str:
    rendered_evaluations = []
    for evaluation in peer_evaluations:
        normalized_evaluation = yaml.safe_dump(evaluation.parsed, sort_keys=False)
        rendered_evaluations.append(
            f"{evaluation.evaluator_label}:\n```yaml\n{normalized_evaluation.strip()}\n```"
        )
    return "\n\n".join(rendered_evaluations)


def _redact_review_data(value: Any, source_diff: str) -> Any:
    if isinstance(value, dict):
        return {key: _redact_review_data(item, source_diff) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_review_data(item, source_diff) for item in value]
    if not isinstance(value, str) or not source_diff:
        return value

    redacted_value = value.replace(source_diff, "[redacted raw diff]")
    for line in source_diff.splitlines():
        stripped_line = line.strip()
        numbered_match = _NUMBERED_DIFF_LINE.match(stripped_line)
        diff_payload = numbered_match.group(1).strip() if numbered_match else stripped_line.lstrip("+- ").strip()
        for sensitive_text in {stripped_line, diff_payload}:
            if len(sensitive_text) >= 3:
                redacted_value = redacted_value.replace(sensitive_text, "[redacted diff line]")
    return redacted_value
