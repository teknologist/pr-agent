import asyncio
import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from pr_agent.config_loader import get_settings
from pr_agent.tools.council_review import (
    CouncilReviewConfig,
    CouncilReviewError,
    CouncilReviewRunner,
    resolve_council_review_config,
)
from pr_agent.tools.pr_reviewer import PRReviewer

_VALID_REVIEW = """review:
  relevant_tests: |
    Yes
  key_issues_to_review: []
  security_concerns: |
    No
"""

_VALID_REVIEW_WITH_FINDING = """review:
  relevant_tests: |
    Yes
  key_issues_to_review:
  - relevant_file: |
      pr_agent/tools/council_review.py
    issue_header: |
      Possible Bug
    issue_content: |
      raw diff with secret line
    start_line: 1
    end_line: 1
  security_concerns: |
    No
"""

_VALID_REVIEW_WITH_SHORT_DIFF_FINDING = _VALID_REVIEW_WITH_FINDING.replace("raw diff with secret line", "secret")
_VALID_REVIEW_WITH_NUMBERED_DIFF_FINDING = _VALID_REVIEW_WITH_FINDING.replace(
    "raw diff with secret line",
    "API_KEY = 'topsecret'",
)

_VALID_PEER_EVALUATION = """peer_evaluation:
  ranking:
  - response_1
  - response_2
  rationale: |
    response_1 is more specific.
"""


def _base_vars():
    return {
        "diff": "",
        "title": "Title",
        "branch": "feature/test",
        "description": "Description",
        "language": "Python",
        "num_pr_files": 1,
        "num_max_findings": 3,
        "require_score": False,
        "require_tests": True,
        "require_estimate_effort_to_review": False,
        "require_estimate_contribution_time_cost": False,
        "require_can_be_split_review": False,
        "require_security_review": True,
        "require_todo_scan": False,
        "question_str": "",
        "answer_str": "",
        "extra_instructions": "",
        "skills_context": "",
        "repo_context": "",
        "commit_messages_str": "",
        "custom_labels": "",
        "enable_custom_labels": False,
        "is_ai_metadata": False,
        "related_tickets": [],
        "duplicate_prompt_examples": False,
        "date": "2026-07-16",
    }


@pytest.fixture
def council_settings():
    settings = get_settings()
    original_council = copy.deepcopy(settings.get("pr_council_review", {}))
    original_review_prompt = copy.deepcopy(dict(settings.pr_review_prompt))
    original_chair_prompt = copy.deepcopy(dict(settings.pr_council_review_prompt))
    try:
        settings.pr_review_prompt.system = "member system"
        settings.pr_review_prompt.user = "member user {{ diff }}"
        settings.pr_council_review_prompt.peer_system = "peer system"
        settings.pr_council_review_prompt.peer_user = "peer user {{ member_reviews }}"
        settings.pr_council_review_prompt.system = "chair system"
        settings.pr_council_review_prompt.user = "chair user {{ member_reviews }} {{ peer_evaluations }}"
        yield settings
    finally:
        settings.set("pr_council_review", original_council)
        settings.pr_review_prompt.clear()
        settings.pr_review_prompt.update(original_review_prompt)
        settings.pr_council_review_prompt.clear()
        settings.pr_council_review_prompt.update(original_chair_prompt)


def test_disabled_configuration_selects_standard_review(council_settings):
    council_settings.set("pr_council_review", {"enabled": False})

    config = resolve_council_review_config()

    assert config.enabled is False
    assert config.warnings == []


def test_absent_configuration_selects_standard_review(council_settings):
    council_settings.set("pr_council_review", {})

    config = resolve_council_review_config()

    assert config.enabled is False
    assert config.warnings == []


@pytest.mark.parametrize(
    "members",
    [
        [{"model": "a"}],
        [{"model": "a"}, {"model": "b"}, {"model": "c"}, {"model": "d"}, {"model": "e"}, {"model": "f"}],
        [{"model": "a"}, {"temperature": 0.1}],
        [{"model": "a"}, {"model": "b", "reasoning_effort": "invalid"}],
        [{"model": "a"}, {"model": "b", "temperatur": 0.1}],
        [{"model": "a"}, {"model": "b", "temperature": float("nan")}],
        [{"model": "a"}, {"model": "b", "temperature": -0.1}],
        [{"model": "a"}, {"model": "b", "temperature": 2.1}],
    ],
)
def test_enabled_configuration_rejects_malformed_rosters_or_inference_settings(council_settings, members):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": members,
        "chair": {"model": "chair"},
    })

    config = resolve_council_review_config()

    assert config.enabled is False
    assert "falling back to Standard Review" in config.warnings[0]


def test_enabled_configuration_rejects_non_table_section(council_settings):
    council_settings.set("pr_council_review", True)

    config = resolve_council_review_config()

    assert config.enabled is False
    assert "section must be a table" in config.warnings[0]


def test_enabled_configuration_rejects_non_boolean_enabled(council_settings):
    council_settings.set("pr_council_review", {
        "enabled": "false",
        "members": [{"model": "model-a"}, {"model": "model-b"}],
        "chair": {"model": "chair"},
    })

    config = resolve_council_review_config()

    assert config.enabled is False
    assert "enabled must be boolean" in config.warnings[0]


def test_enabled_configuration_accepts_members_and_chair(council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [
            {"model": "model-a", "temperature": 0.1, "reasoning_effort": "high"},
            {"model": "model-b", "temperature": 0.2},
        ],
        "chair": {"model": "chair", "reasoning_effort": "medium"},
    })

    config = resolve_council_review_config()

    assert config.enabled is True
    assert [member.model for member in config.members] == ["model-a", "model-b"]
    assert config.chair.model == "chair"


def test_peer_evaluation_is_enabled_by_default_and_can_be_disabled(council_settings):
    section = {
        "enabled": True,
        "members": [{"model": "model-a"}, {"model": "model-b"}],
        "chair": {"model": "chair"},
    }
    council_settings.set("pr_council_review", section)

    assert resolve_council_review_config().peer_evaluation is True

    section["peer_evaluation"] = False
    council_settings.set("pr_council_review", section)

    assert resolve_council_review_config().peer_evaluation is False


def test_peer_evaluation_rejects_non_boolean_configuration(council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": "false",
        "members": [{"model": "model-a"}, {"model": "model-b"}],
        "chair": {"model": "chair"},
    })

    config = resolve_council_review_config()

    assert config.enabled is False
    assert "peer_evaluation must be boolean" in config.warnings[0]


class FakeAiHandler:
    responses_by_model = {}
    calls = []
    active_calls = 0
    max_active_calls = 0
    active_calls_by_stage = {}
    max_active_calls_by_stage = {}
    instances = 0

    def __init__(self):
        FakeAiHandler.instances += 1
        self.main_pr_language = None

    @property
    def deployment_id(self):
        return None

    async def chat_completion(self, model, system, user, temperature=0.2, img_path=None):
        raise AssertionError("runner should request metadata-aware completions")

    async def chat_completion_with_metadata(
        self,
        model,
        system,
        user,
        temperature=None,
        img_path=None,
        inference_settings=None,
    ):
        stage = "peer" if system == "peer system" else "chair" if system == "chair system" else "member"
        FakeAiHandler.calls.append({
            "model": model,
            "stage": stage,
            "system": system,
            "user": user,
            "inference_settings": inference_settings,
            "deployment_id": get_settings().get("openai.deployment_id", None),
        })
        FakeAiHandler.active_calls += 1
        FakeAiHandler.max_active_calls = max(FakeAiHandler.max_active_calls, FakeAiHandler.active_calls)
        FakeAiHandler.active_calls_by_stage[stage] = FakeAiHandler.active_calls_by_stage.get(stage, 0) + 1
        FakeAiHandler.max_active_calls_by_stage[stage] = max(
            FakeAiHandler.max_active_calls_by_stage.get(stage, 0),
            FakeAiHandler.active_calls_by_stage[stage],
        )
        await asyncio.sleep(0.01)
        FakeAiHandler.active_calls -= 1
        FakeAiHandler.active_calls_by_stage[stage] -= 1
        response = FakeAiHandler.responses_by_model.get(f"{model}:{stage}", FakeAiHandler.responses_by_model[model])
        if isinstance(response, BaseException):
            raise response
        return SimpleNamespace(response=response, finish_reason="stop", metadata={"warnings": []})


def _reset_fake_handler(responses_by_model):
    FakeAiHandler.responses_by_model = responses_by_model
    FakeAiHandler.calls = []
    FakeAiHandler.active_calls = 0
    FakeAiHandler.max_active_calls = 0
    FakeAiHandler.active_calls_by_stage = {}
    FakeAiHandler.max_active_calls_by_stage = {}
    FakeAiHandler.instances = 0


class HandlerManagedTimeoutAiHandler:
    manages_ai_timeout = True

    def __init__(self):
        self.main_pr_language = None

    @property
    def deployment_id(self):
        return None

    async def chat_completion_with_metadata(
        self,
        model,
        system,
        user,
        temperature=None,
        img_path=None,
        inference_settings=None,
    ):
        await asyncio.sleep(0.02)
        return SimpleNamespace(response=_VALID_REVIEW, finish_reason="stop", metadata={"warnings": []})


class LifecycleAiHandler:
    plans = {}
    events = []
    active_calls = 0
    max_active_calls = 0
    cancelled_calls = 0

    def __init__(self):
        self.main_pr_language = None

    @property
    def deployment_id(self):
        return None

    async def chat_completion_with_metadata(
        self,
        model,
        system,
        user,
        temperature=None,
        img_path=None,
        inference_settings=None,
    ):
        stage = "peer" if system == "peer system" else "chair" if system == "chair system" else "member"
        key = f"{model}:{stage}"
        delay, response = self.plans[key]
        self.events.append(("start", key))
        type(self).active_calls += 1
        type(self).max_active_calls = max(type(self).max_active_calls, type(self).active_calls)
        try:
            await asyncio.sleep(delay)
            if isinstance(response, BaseException):
                raise response
            self.events.append(("finish", key))
            return SimpleNamespace(
                response=response,
                finish_reason="stop",
                metadata={"token_usage": {"total_tokens": 17}, "warnings": []},
            )
        except asyncio.CancelledError:
            type(self).cancelled_calls += 1
            self.events.append(("cancel", key))
            raise
        finally:
            type(self).active_calls -= 1


def _reset_lifecycle_handler(plans):
    LifecycleAiHandler.plans = plans
    LifecycleAiHandler.events = []
    LifecycleAiHandler.active_calls = 0
    LifecycleAiHandler.max_active_calls = 0
    LifecycleAiHandler.cancelled_calls = 0


async def _wait_for_lifecycle_event(expected_event):
    async def wait_for_event():
        while expected_event not in LifecycleAiHandler.events:
            await asyncio.sleep(0)

    await asyncio.wait_for(wait_for_event(), timeout=1)


def _runner(config, git_provider=None, ai_handler_factory=FakeAiHandler):
    return CouncilReviewRunner(
        config=config,
        git_provider=git_provider or SimpleNamespace(),
        token_handler=SimpleNamespace(),
        vars=_base_vars(),
        ai_handler_factory=ai_handler_factory,
        main_language="Python",
    )


def _peer_enabled_config(council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": True,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    return resolve_council_review_config()


def test_successful_council_uses_member_models_model_specific_diffs_and_returns_metadata(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    diff_models = []
    monkeypatch.setattr(
        "pr_agent.tools.council_review.get_pr_diff",
        lambda git_provider, token_handler, model, **kwargs: diff_models.append(model) or f"diff-for-{model}",
    )
    review_with_echoed_diff = f"{_VALID_REVIEW}\nraw_pr_diff: |\n  raw diff\n"
    _reset_fake_handler({"member-a": review_with_echoed_diff, "member-b": _VALID_REVIEW, "chair": _VALID_REVIEW})

    result = asyncio.run(_runner(config).run())

    parsed_prediction = yaml.safe_load(result.prediction)
    assert parsed_prediction["review"]["key_issues_to_review"] == []
    assert parsed_prediction["review"]["relevant_tests"].strip() == "Yes"
    assert parsed_prediction["review"]["security_concerns"].strip() == "No"
    assert result.metadata["strategy"] == "council_review"
    assert result.metadata["successful_member_count"] == 2
    assert diff_models == ["member-a", "member-b"]
    assert FakeAiHandler.max_active_calls > 1
    assert [call["model"] for call in FakeAiHandler.calls] == ["member-a", "member-b", "chair"]
    assert FakeAiHandler.instances == 1
    assert "diff-for-member-a" in FakeAiHandler.calls[0]["user"]
    assert "diff-for-member-b" in FakeAiHandler.calls[1]["user"]
    assert "raw diff" not in FakeAiHandler.calls[-1]["user"]


def test_disabled_peer_evaluation_skips_stage_and_chair_receives_no_evaluations(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({"member-a": _VALID_REVIEW, "member-b": _VALID_REVIEW, "chair": _VALID_REVIEW})

    result = asyncio.run(_runner(config).run())

    chair_call = [call for call in FakeAiHandler.calls if call["stage"] == "chair"][0]
    assert [call for call in FakeAiHandler.calls if call["stage"] == "peer"] == []
    assert result.metadata["peer_evaluation_enabled"] is False
    assert result.metadata["successful_peer_evaluation_count"] == 0
    assert result.metadata["failed_peer_evaluation_count"] == 0
    assert "evaluator_" not in chair_call["user"]


def test_peer_evaluations_are_anonymized_concurrent_and_available_to_chair(monkeypatch, council_settings):
    config = _peer_enabled_config(council_settings)
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw secret diff")
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": _VALID_REVIEW,
        "member-a:peer": _VALID_PEER_EVALUATION,
        "member-b:peer": _VALID_PEER_EVALUATION,
        "chair": _VALID_REVIEW,
    })

    result = asyncio.run(_runner(config).run())

    peer_calls = [call for call in FakeAiHandler.calls if call["stage"] == "peer"]
    chair_call = [call for call in FakeAiHandler.calls if call["stage"] == "chair"][0]
    assert [call["model"] for call in peer_calls] == ["member-a", "member-b"]
    assert FakeAiHandler.max_active_calls_by_stage["peer"] == 2
    assert all("response_1" in call["user"] and "response_2" in call["user"] for call in peer_calls)
    assert all("member-a" not in call["user"] and "member-b" not in call["user"] for call in peer_calls)
    assert all("raw secret diff" not in call["user"] for call in peer_calls)
    assert "peer_evaluation" in chair_call["user"]
    assert "response_1" in chair_call["user"]
    assert "raw secret diff" not in chair_call["user"]
    assert result.metadata["successful_peer_evaluation_count"] == 2
    assert result.metadata["failed_peer_evaluation_count"] == 0


def test_all_configured_members_evaluate_gapped_anonymous_success_labels(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": True,
        "members": [{"model": "member-a"}, {"model": "member-b"}, {"model": "member-c"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    peer_evaluation = _VALID_PEER_EVALUATION.replace("response_2", "response_3")
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": "not yaml: [",
        "member-c": _VALID_REVIEW,
        "member-a:peer": peer_evaluation,
        "member-b:peer": peer_evaluation,
        "member-c:peer": peer_evaluation,
        "chair": _VALID_REVIEW,
    })

    result = asyncio.run(_runner(config).run())

    peer_calls = [call for call in FakeAiHandler.calls if call["stage"] == "peer"]
    assert [call["model"] for call in peer_calls] == ["member-a", "member-b", "member-c"]
    assert all("response_1" in call["user"] and "response_3" in call["user"] for call in peer_calls)
    assert all("response_2" not in call["user"] for call in peer_calls)
    assert result.metadata["successful_member_count"] == 2
    assert result.metadata["successful_peer_evaluation_count"] == 3


@pytest.mark.parametrize(
    ("peer_a", "peer_b", "successful_count", "failed_count"),
    [
        (_VALID_PEER_EVALUATION, RuntimeError("peer unavailable"), 1, 1),
        ("not yaml: [", RuntimeError("peer unavailable"), 0, 2),
    ],
)
def test_peer_evaluation_failures_are_best_effort(
    monkeypatch,
    council_settings,
    peer_a,
    peer_b,
    successful_count,
    failed_count,
):
    config = _peer_enabled_config(council_settings)
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": _VALID_REVIEW,
        "member-a:peer": peer_a,
        "member-b:peer": peer_b,
        "chair": _VALID_REVIEW,
    })

    result = asyncio.run(_runner(config).run())

    chair_call = [call for call in FakeAiHandler.calls if call["stage"] == "chair"][0]
    assert result.metadata["successful_peer_evaluation_count"] == successful_count
    assert result.metadata["failed_peer_evaluation_count"] == failed_count
    assert chair_call["user"].count("evaluator_") == successful_count


@pytest.mark.parametrize(
    "ranking",
    [
        ["response_1"],
        ["response_1", "response_1"],
        ["response_1", "unknown_response"],
    ],
)
def test_semantically_malformed_peer_rankings_are_best_effort(
    monkeypatch,
    council_settings,
    ranking,
):
    config = _peer_enabled_config(council_settings)
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    malformed_evaluation = yaml.safe_dump({
        "peer_evaluation": {
            "ranking": ranking,
            "rationale": "Malformed ranking must not reach the chair.",
        }
    })
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": _VALID_REVIEW,
        "member-a:peer": malformed_evaluation,
        "member-b:peer": _VALID_PEER_EVALUATION,
        "chair": _VALID_REVIEW,
    })

    result = asyncio.run(_runner(config).run())

    chair_call = [call for call in FakeAiHandler.calls if call["stage"] == "chair"][0]
    assert result.metadata["successful_peer_evaluation_count"] == 1
    assert result.metadata["failed_peer_evaluation_count"] == 1
    assert "evaluator_1" not in chair_call["user"]
    assert "evaluator_2" in chair_call["user"]


def test_member_and_peer_calls_do_not_use_global_fallback_models(monkeypatch, council_settings):
    original_fallback_models = copy.deepcopy(council_settings.config.fallback_models)
    council_settings.config.fallback_models = ["fallback-model"]
    config = _peer_enabled_config(council_settings)
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": _VALID_REVIEW,
        "member-a:peer": _VALID_PEER_EVALUATION,
        "member-b:peer": _VALID_PEER_EVALUATION,
        "chair": _VALID_REVIEW,
    })

    try:
        asyncio.run(_runner(config).run())
    finally:
        council_settings.config.fallback_models = original_fallback_models

    assert "fallback-model" not in [call["model"] for call in FakeAiHandler.calls]


def test_failed_member_and_peer_calls_do_not_retry_with_global_fallback_models(monkeypatch, council_settings):
    original_fallback_models = copy.deepcopy(council_settings.config.fallback_models)
    council_settings.config.fallback_models = ["global-fallback"]
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": True,
        "members": [{"model": "member-a"}, {"model": "member-b"}, {"model": "member-c"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    peer_ranking = _VALID_PEER_EVALUATION.replace("response_2", "response_3")
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": RuntimeError("member unavailable"),
        "member-c": _VALID_REVIEW,
        "member-a:peer": peer_ranking,
        "member-b:peer": RuntimeError("peer unavailable"),
        "member-c:peer": peer_ranking,
        "chair": _VALID_REVIEW,
        "global-fallback": _VALID_REVIEW,
    })

    try:
        result = asyncio.run(_runner(config).run())
    finally:
        council_settings.config.fallback_models = original_fallback_models

    assert result.metadata["failed_member_count"] == 1
    assert result.metadata["failed_peer_evaluation_count"] == 1
    assert "global-fallback" not in [call["model"] for call in FakeAiHandler.calls]


def test_incremental_council_uses_current_scoped_provider_evidence_for_each_member(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    git_provider = SimpleNamespace(incremental=SimpleNamespace(is_incremental=True))
    evidence = []

    def get_incremental_diff(provider, token_handler, model, **kwargs):
        assert provider is git_provider
        assert provider.incremental.is_incremental is True
        evidence.append((model, f"incremental-diff-for-{model}"))
        return evidence[-1][1]

    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", get_incremental_diff)
    _reset_fake_handler({"member-a": _VALID_REVIEW, "member-b": _VALID_REVIEW, "chair": _VALID_REVIEW})

    asyncio.run(_runner(config, git_provider).run())

    assert evidence == [
        ("member-a", "incremental-diff-for-member-a"),
        ("member-b", "incremental-diff-for-member-b"),
    ]
    assert "incremental-diff-for-member-a" in FakeAiHandler.calls[0]["user"]
    assert "incremental-diff-for-member-b" in FakeAiHandler.calls[1]["user"]


@pytest.mark.parametrize(
    ("source_diff", "member_review", "secret_text"),
    [
        ("raw diff with secret line", _VALID_REVIEW_WITH_FINDING, "raw diff with secret line"),
        ("+secret", _VALID_REVIEW_WITH_SHORT_DIFF_FINDING, "secret"),
        ("12 +API_KEY = 'topsecret'", _VALID_REVIEW_WITH_NUMBERED_DIFF_FINDING, "API_KEY = 'topsecret'"),
    ],
)
def test_member_review_diff_content_is_redacted_before_chair(
    monkeypatch,
    council_settings,
    source_diff,
    member_review,
    secret_text,
):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: source_diff)
    _reset_fake_handler({
        "member-a": member_review,
        "member-b": _VALID_REVIEW,
        "chair": _VALID_REVIEW,
    })

    result = asyncio.run(_runner(config).run())

    assert result.metadata["successful_member_count"] == 2
    assert secret_text not in FakeAiHandler.calls[-1]["user"]
    assert "[redacted" in FakeAiHandler.calls[-1]["user"]


def test_malformed_member_does_not_count_toward_quorum_but_successful_reviews_go_to_chair(
    monkeypatch,
    council_settings,
):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}, {"model": "member-c"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": "not yaml: [",
        "member-c": _VALID_REVIEW,
        "chair": _VALID_REVIEW,
    })

    result = asyncio.run(_runner(config).run())

    chair_call = FakeAiHandler.calls[-1]
    assert result.metadata["successful_member_count"] == 2
    assert result.metadata["failed_member_count"] == 1
    assert chair_call["model"] == "chair"
    assert chair_call["user"].count("response_") == 2
    assert "raw diff" not in chair_call["user"]


@pytest.mark.parametrize(
    "invalid_review",
    [
        "review: {}",
        """review:
  relevant_tests: |
    Yes
  key_issues_to_review:
  - scalar issue
  security_concerns: |
    No
""",
        """review:
  relevant_tests: |
    Yes
  key_issues_to_review:
  - relevant_file: council_review.py
    issue_header: Invalid line
    issue_content: start_line must be an integer
    start_line: []
    end_line: 1
  security_concerns: |
    No
""",
        """review:
  relevant_tests: |
    Yes
  key_issues_to_review: []
  security_concerns: |
    No
  raw_pr_diff: |
    raw diff
""",
    ],
)
def test_structurally_invalid_member_does_not_count_toward_quorum(monkeypatch, council_settings, invalid_review):
    logger = MagicMock()
    monkeypatch.setattr("pr_agent.tools.council_review.get_logger", lambda: logger)
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({"member-a": invalid_review, "member-b": _VALID_REVIEW, "chair": _VALID_REVIEW})

    with pytest.raises(CouncilReviewError, match="fewer than two"):
        asyncio.run(_runner(config).run())

    assert [call["model"] for call in FakeAiHandler.calls] == ["member-a", "member-b"]
    fallback_event = next(
        call.kwargs["artifact"]
        for call in logger.info.call_args_list
        if call.args[0] == "Council Review fallback evaluated"
    )
    assert fallback_event["fallback_decisions"] == {
        "standard_review": "not_used",
        "chair_fallback": "not_evaluated",
        "member_fallback": "not_evaluated",
    }


@pytest.mark.asyncio
async def test_member_stage_waits_for_slow_failure_before_starting_chair(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}, {"model": "member-c"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_lifecycle_handler({
        "member-a:member": (0.01, _VALID_REVIEW),
        "member-b:member": (0.03, RuntimeError("late failure")),
        "member-c:member": (0.02, _VALID_REVIEW),
        "chair:chair": (0, _VALID_REVIEW),
    })

    result = await _runner(config, ai_handler_factory=LifecycleAiHandler).run()

    assert LifecycleAiHandler.events.index(("start", "chair:chair")) > LifecycleAiHandler.events.index(
        ("finish", "member-c:member")
    )
    assert result.metadata["quorum"] == {"required": 2, "successful": 2, "met": True}
    assert [call["outcome"] for call in result.metadata["calls"][:3]].count("failure") == 1
    assert result.metadata["calls"][0]["token_usage"] == {"total_tokens": 17}


@pytest.mark.asyncio
async def test_parse_failure_records_available_token_usage(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}, {"model": "member-c"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_lifecycle_handler({
        "member-a:member": (0, _VALID_REVIEW),
        "member-b:member": (0, "not a structured review"),
        "member-c:member": (0, _VALID_REVIEW),
        "chair:chair": (0, _VALID_REVIEW),
    })

    result = await _runner(config, ai_handler_factory=LifecycleAiHandler).run()

    member_b = next(call for call in result.metadata["calls"] if call["model"] == "member-b")
    assert member_b["outcome"] == "failure"
    assert member_b["token_usage"] == {"total_tokens": 17}


@pytest.mark.asyncio
async def test_runner_preserves_handler_managed_timeout_budget(monkeypatch, council_settings):
    original_timeout = council_settings.config.ai_timeout
    council_settings.config.ai_timeout = 0.01
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")

    try:
        result = await _runner(config, ai_handler_factory=HandlerManagedTimeoutAiHandler).run()
    finally:
        council_settings.config.ai_timeout = original_timeout

    assert result.metadata["successful_member_count"] == 2
    assert all(call["outcome"] == "success" for call in result.metadata["calls"])


@pytest.mark.asyncio
async def test_member_timeout_is_recorded_and_stage_settles(monkeypatch, council_settings):
    original_timeout = council_settings.config.ai_timeout
    council_settings.config.ai_timeout = 0.01
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}, {"model": "member-c"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_lifecycle_handler({
        "member-a:member": (0, _VALID_REVIEW),
        "member-b:member": (10, _VALID_REVIEW),
        "member-c:member": (0, _VALID_REVIEW),
        "chair:chair": (0, _VALID_REVIEW),
    })

    try:
        result = await _runner(config, ai_handler_factory=LifecycleAiHandler).run()
    finally:
        council_settings.config.ai_timeout = original_timeout

    member_b = next(call for call in result.metadata["calls"] if call["model"] == "member-b")
    assert member_b["outcome"] == "timeout"
    assert LifecycleAiHandler.cancelled_calls == 1
    assert LifecycleAiHandler.active_calls == 0


@pytest.mark.asyncio
async def test_review_cancellation_cancels_all_outstanding_member_tasks(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": f"member-{index}"} for index in range(5)],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_lifecycle_handler({
        **{f"member-{index}:member": (10, _VALID_REVIEW) for index in range(5)},
        "chair:chair": (0, _VALID_REVIEW),
    })
    task = asyncio.create_task(_runner(config, ai_handler_factory=LifecycleAiHandler).run())
    await _wait_for_lifecycle_event(("start", "member-4:member"))

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=1)

    assert LifecycleAiHandler.cancelled_calls == 5
    assert LifecycleAiHandler.active_calls == 0
    assert ("start", "chair:chair") not in LifecycleAiHandler.events


@pytest.mark.asyncio
async def test_review_cancellation_cancels_all_outstanding_peer_tasks(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": True,
        "members": [{"model": f"member-{index}"} for index in range(5)],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    peer_evaluation = yaml.safe_dump({
        "peer_evaluation": {
            "ranking": [f"response_{index}" for index in range(1, 6)],
            "rationale": "Complete ranking.",
        }
    })
    _reset_lifecycle_handler({
        **{f"member-{index}:member": (0, _VALID_REVIEW) for index in range(5)},
        **{f"member-{index}:peer": (10, peer_evaluation) for index in range(5)},
        "chair:chair": (0, _VALID_REVIEW),
    })
    task = asyncio.create_task(_runner(config, ai_handler_factory=LifecycleAiHandler).run())
    await _wait_for_lifecycle_event(("start", "member-4:peer"))

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=1)

    peer_cancellations = [event for event in LifecycleAiHandler.events if event[0] == "cancel"]
    assert len(peer_cancellations) == 5
    assert LifecycleAiHandler.active_calls == 0
    assert ("start", "chair:chair") not in LifecycleAiHandler.events


@pytest.mark.asyncio
async def test_review_cancellation_cancels_outstanding_chair_task(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_lifecycle_handler({
        "member-a:member": (0, _VALID_REVIEW),
        "member-b:member": (0, _VALID_REVIEW),
        "chair:chair": (10, _VALID_REVIEW),
    })
    task = asyncio.create_task(_runner(config, ai_handler_factory=LifecycleAiHandler).run())
    await _wait_for_lifecycle_event(("start", "chair:chair"))

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=1)

    assert LifecycleAiHandler.cancelled_calls == 1
    assert LifecycleAiHandler.active_calls == 0


def test_cancelled_member_is_a_failed_result_and_does_not_corrupt_quorum(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}, {"model": "member-c"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": asyncio.CancelledError(),
        "member-c": _VALID_REVIEW,
        "chair": _VALID_REVIEW,
    })

    result = asyncio.run(_runner(config).run())

    assert result.metadata["successful_member_count"] == 2
    assert result.metadata["failed_member_count"] == 1
    assert [call["model"] for call in FakeAiHandler.calls] == ["member-a", "member-b", "member-c", "chair"]


def test_peer_enabled_five_member_run_never_exceeds_hard_cap(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": True,
        "members": [{"model": f"member-{index}"} for index in range(5)],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    five_member_peer_evaluation = yaml.safe_dump({
        "peer_evaluation": {
            "ranking": [f"response_{index}" for index in range(1, 6)],
            "rationale": "Complete ranking.",
        }
    })
    _reset_lifecycle_handler({
        **{f"member-{index}:member": (0.01, _VALID_REVIEW) for index in range(5)},
        **{f"member-{index}:peer": (0.01, five_member_peer_evaluation) for index in range(5)},
        "chair:chair": (0, _VALID_REVIEW),
    })

    result = asyncio.run(_runner(config, ai_handler_factory=LifecycleAiHandler).run())

    assert result.metadata["member_count"] == 5
    assert LifecycleAiHandler.max_active_calls == 5


def test_council_logs_and_metadata_exclude_raw_outputs(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}, {"model": "member-c"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw prompt")
    logger = MagicMock()
    monkeypatch.setattr("pr_agent.tools.council_review.get_logger", lambda: logger)
    secret = "raw member peer ranking prompt chair output"
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": RuntimeError(secret),
        "member-c": _VALID_REVIEW,
        "chair": _VALID_REVIEW,
    })

    result = asyncio.run(_runner(config).run())

    assert secret not in repr(logger.mock_calls)
    assert secret not in repr(result.metadata)
    assert all(
        "response" not in call and "prompt" not in call and "ranking" not in call
        for call in result.metadata["calls"]
    )
    assert result.metadata["fallback_decisions"] == {
        "standard_review": "not_used",
        "chair_fallback": "not_used",
        "member_fallback": "not_used",
    }
    assert all({"strategy", "stage", "role", "model", "duration_ms", "outcome"} <= set(call)
               for call in result.metadata["calls"])


def test_malformed_member_output_is_redacted_from_parser_logs(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}, {"model": "member-c"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    logger = MagicMock()
    monkeypatch.setattr("pr_agent.tools.council_review.get_logger", lambda: logger)
    monkeypatch.setattr("pr_agent.algo.utils.get_logger", lambda: logger)
    secret = "raw member prompt echoed into malformed output"
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": f"```yaml\nreview: [ {secret}\n```",
        "member-c": _VALID_REVIEW,
        "chair": _VALID_REVIEW,
    })

    result = asyncio.run(_runner(config).run())

    assert result.metadata["successful_member_count"] == 2
    assert secret not in repr(logger.mock_calls)


def test_numeric_and_boolean_standard_review_scalars_are_normalized(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    config_vars = _base_vars()
    config_vars["require_score"] = True
    config_vars["require_estimate_effort_to_review"] = True
    scalar_review = """review:
  estimated_effort_to_review_[1-5]: '3'
  score: 89
  relevant_tests: Yes
  key_issues_to_review: []
  security_concerns: No
"""
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({"member-a": scalar_review, "member-b": scalar_review, "chair": scalar_review})

    result = asyncio.run(CouncilReviewRunner(
        config=config,
        git_provider=SimpleNamespace(),
        token_handler=SimpleNamespace(),
        vars=config_vars,
        ai_handler_factory=FakeAiHandler,
        main_language="Python",
    ).run())

    parsed_prediction = yaml.safe_load(result.prediction)
    assert result.metadata["successful_member_count"] == 2
    assert parsed_prediction["review"]["estimated_effort_to_review_[1-5]"] == 3
    assert parsed_prediction["review"]["score"] == "89"
    assert parsed_prediction["review"]["relevant_tests"] == "Yes"
    assert parsed_prediction["review"]["security_concerns"] == "No"


def test_optional_prompt_fields_are_required_when_enabled(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    config_vars = _base_vars()
    config_vars["require_score"] = True
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({"member-a": _VALID_REVIEW, "member-b": _VALID_REVIEW, "chair": _VALID_REVIEW})

    with pytest.raises(CouncilReviewError, match="fewer than two"):
        asyncio.run(CouncilReviewRunner(
            config=config,
            git_provider=SimpleNamespace(),
            token_handler=SimpleNamespace(),
            vars=config_vars,
            ai_handler_factory=FakeAiHandler,
            main_language="Python",
        ).run())

    assert [call["model"] for call in FakeAiHandler.calls] == ["member-a", "member-b"]


def test_chair_fallbacks_are_attempted_in_order_with_chair_inference_settings(monkeypatch, council_settings):
    original_fallback_models = copy.deepcopy(council_settings.config.fallback_models)
    original_deployment_id = council_settings.get("openai.deployment_id", None)
    original_fallback_deployments = copy.deepcopy(council_settings.get("openai.fallback_deployments", []))
    council_settings.config.fallback_models = ["fallback-a", "fallback-b"]
    council_settings.set("openai.deployment_id", "chair-deployment")
    council_settings.set("openai.fallback_deployments", ["fallback-a-deployment", "fallback-b-deployment"])
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair", "temperature": 0.1, "reasoning_effort": "high"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": _VALID_REVIEW,
        "chair": RuntimeError("chair unavailable"),
        "fallback-a": RuntimeError("first fallback unavailable"),
        "fallback-b": _VALID_REVIEW,
    })

    try:
        result = asyncio.run(_runner(config).run())
        assert council_settings.get("openai.deployment_id", None) == "chair-deployment"
    finally:
        council_settings.config.fallback_models = original_fallback_models
        council_settings.set("openai.deployment_id", original_deployment_id)
        council_settings.set("openai.fallback_deployments", original_fallback_deployments)

    chair_calls = [call for call in FakeAiHandler.calls if call["stage"] == "chair"]
    assert [call["model"] for call in chair_calls] == ["chair", "fallback-a", "fallback-b"]
    assert [call["deployment_id"] for call in chair_calls] == [
        "chair-deployment",
        "fallback-a-deployment",
        "fallback-b-deployment",
    ]
    assert all(call["inference_settings"] == config.chair.inference_settings for call in chair_calls)
    assert result.metadata["chair_model"] == "fallback-b"
    assert result.metadata["synthesis_strategy"] == "chair"
    assert result.metadata["fallback_decisions"] == {
        "standard_review": "not_used",
        "chair_fallback": "used",
        "member_fallback": "not_used",
    }


def test_member_fallback_uses_borda_winner_after_all_chairs_fail(monkeypatch, council_settings):
    original_fallback_models = copy.deepcopy(council_settings.config.fallback_models)
    council_settings.config.fallback_models = ["fallback-chair"]
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": True,
        "members": [{"model": "member-a"}, {"model": "member-b"}, {"model": "member-c"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    review_a = _VALID_REVIEW.replace("Yes", "member-a")
    review_b = _VALID_REVIEW.replace("Yes", "member-b")
    review_c = _VALID_REVIEW.replace("Yes", "member-c")
    ranking_a = _VALID_PEER_EVALUATION.replace(
        "  - response_1\n  - response_2",
        "  - response_2\n  - response_1\n  - response_3",
    )
    ranking_b = ranking_a.replace(
        "  - response_2\n  - response_1\n  - response_3",
        "  - response_2\n  - response_3\n  - response_1",
    )
    _reset_fake_handler({
        "member-a": review_a,
        "member-b": review_b,
        "member-c": review_c,
        "member-a:peer": ranking_a,
        "member-b:peer": ranking_b,
        "member-c:peer": RuntimeError("peer unavailable"),
        "chair": RuntimeError("chair unavailable"),
        "fallback-chair": RuntimeError("fallback unavailable"),
    })

    try:
        result = asyncio.run(_runner(config).run())
    finally:
        council_settings.config.fallback_models = original_fallback_models

    assert yaml.safe_load(result.prediction)["review"]["relevant_tests"].strip() == "member-b"
    assert result.metadata["chair_model"] is None
    assert result.metadata["synthesis_strategy"] == "member_fallback"
    assert result.metadata["fallback_decisions"] == {
        "standard_review": "not_used",
        "chair_fallback": "exhausted",
        "member_fallback": "used",
    }


def test_member_fallback_breaks_top_borda_tie_by_configured_member_order(monkeypatch, council_settings):
    original_fallback_models = copy.deepcopy(council_settings.config.fallback_models)
    council_settings.config.fallback_models = []
    config = _peer_enabled_config(council_settings)
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    reverse_ranking = _VALID_PEER_EVALUATION.replace(
        "  - response_1\n  - response_2",
        "  - response_2\n  - response_1",
    )
    _reset_fake_handler({
        "member-a": _VALID_REVIEW.replace("Yes", "first-member"),
        "member-b": _VALID_REVIEW.replace("Yes", "second-member"),
        "member-a:peer": _VALID_PEER_EVALUATION,
        "member-b:peer": reverse_ranking,
        "chair": RuntimeError("chair unavailable"),
    })

    try:
        result = asyncio.run(_runner(config).run())
    finally:
        council_settings.config.fallback_models = original_fallback_models

    assert yaml.safe_load(result.prediction)["review"]["relevant_tests"].strip() == "first-member"
    assert result.metadata["synthesis_strategy"] == "member_fallback"


@pytest.mark.parametrize(
    "peer_responses",
    [
        None,
        [_VALID_PEER_EVALUATION, RuntimeError("peer unavailable")],
        ["not yaml: [", "not yaml: ["],
    ],
    ids=["absent", "insufficient", "malformed"],
)
def test_exhausted_chairs_without_two_valid_rankings_terminate(monkeypatch, council_settings, peer_responses):
    original_fallback_models = copy.deepcopy(council_settings.config.fallback_models)
    logger = MagicMock()
    monkeypatch.setattr("pr_agent.tools.council_review.get_logger", lambda: logger)
    council_settings.config.fallback_models = ["fallback-chair"]
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": peer_responses is not None,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    responses = {
        "member-a": _VALID_REVIEW,
        "member-b": _VALID_REVIEW,
        "chair": RuntimeError("chair unavailable"),
        "fallback-chair": RuntimeError("fallback unavailable"),
    }
    if peer_responses is not None:
        responses["member-a:peer"], responses["member-b:peer"] = peer_responses
    _reset_fake_handler(responses)

    try:
        with pytest.raises(CouncilReviewError, match="failed during chair synthesis"):
            asyncio.run(_runner(config).run())
    finally:
        council_settings.config.fallback_models = original_fallback_models

    assert [call["model"] for call in FakeAiHandler.calls if call["stage"] == "chair"] == [
        "chair",
        "fallback-chair",
    ]
    fallback_event = next(
        call.kwargs["artifact"]
        for call in logger.info.call_args_list
        if call.args[0] == "Council Review fallback evaluated"
    )
    assert fallback_event["quorum"] == {"required": 2, "successful": 2, "met": True}
    assert fallback_event["fallback_decisions"] == {
        "standard_review": "not_used",
        "chair_fallback": "exhausted",
        "member_fallback": "unavailable",
    }


def test_chair_runtime_failure_is_sanitized_for_reviewer_publication(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    original_fallback_models = copy.deepcopy(council_settings.config.fallback_models)
    council_settings.config.fallback_models = []
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({
        "member-a": _VALID_REVIEW,
        "member-b": _VALID_REVIEW,
        "chair": RuntimeError("provider secret should not be published"),
    })

    try:
        with pytest.raises(CouncilReviewError, match="failed during chair synthesis") as exc_info:
            asyncio.run(_runner(config).run())
    finally:
        council_settings.config.fallback_models = original_fallback_models

    assert "provider secret" not in exc_info.value.public_message


def test_ticket_prompt_examples_match_the_structured_review_schema():
    prompt = get_settings().pr_review_prompt.system + get_settings().pr_review_prompt.user

    assert "overall_compliance_level" not in prompt
    assert prompt.count("requires_further_human_verification") == 3


def test_no_quorum_raises_without_chair_or_standard_review_fallback(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "peer_evaluation": False,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({"member-a": _VALID_REVIEW, "member-b": "not yaml: [", "chair": _VALID_REVIEW})

    with pytest.raises(CouncilReviewError, match="fewer than two"):
        asyncio.run(_runner(config).run())

    assert [call["model"] for call in FakeAiHandler.calls] == ["member-a", "member-b"]


def _reviewer_for_integration_run():
    git_provider = MagicMock()
    git_provider.get_files.return_value = [SimpleNamespace(filename="changed.py")]
    reviewer = PRReviewer.__new__(PRReviewer)
    reviewer.git_provider = git_provider
    reviewer.pr_url = "https://example/pr/1"
    reviewer.incremental = SimpleNamespace(is_incremental=False)
    reviewer.is_answer = False
    reviewer.is_auto = False
    reviewer.vars = {}
    reviewer.token_handler = SimpleNamespace()
    reviewer.ai_handler_factory = FakeAiHandler
    reviewer.main_language = "Python"
    reviewer.prediction = None
    reviewer._prepare_pr_review = MagicMock(return_value="prepared review")
    reviewer._should_publish_review_no_suggestions = MagicMock(return_value=False)
    return reviewer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "section",
    [
        {},
        {"enabled": False},
        {"enabled": True, "members": [], "chair": {"model": "chair"}},
    ],
)
async def test_pr_reviewer_runs_standard_review_for_absent_disabled_or_invalid_config(
    monkeypatch,
    council_settings,
    section,
):
    original_publish_output = council_settings.config.publish_output
    council_settings.config.publish_output = False
    council_settings.set("pr_council_review", section)
    reviewer = _reviewer_for_integration_run()
    standard_review = AsyncMock()

    async def run_standard_review(*args, **kwargs):
        reviewer.prediction = _VALID_REVIEW
        await standard_review(*args, **kwargs)

    monkeypatch.setattr("pr_agent.tools.pr_reviewer.extract_and_cache_pr_tickets", AsyncMock())
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.retry_with_fallback_models", run_standard_review)
    try:
        await reviewer.run()
    finally:
        council_settings.config.publish_output = original_publish_output

    standard_review.assert_awaited_once()


@pytest.mark.asyncio
async def test_pr_reviewer_answer_never_resolves_or_runs_council(monkeypatch, council_settings):
    original_publish_output = council_settings.config.publish_output
    council_settings.config.publish_output = False
    council_settings.set("pr_council_review", {
        "enabled": True,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    reviewer = _reviewer_for_integration_run()
    reviewer.is_answer = True
    reviewer.prediction = _VALID_REVIEW
    standard_review = AsyncMock()
    resolve_config = MagicMock(side_effect=AssertionError("answer mode must not resolve Council Review"))

    monkeypatch.setattr("pr_agent.tools.pr_reviewer.extract_and_cache_pr_tickets", AsyncMock())
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.resolve_council_review_config", resolve_config)
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.CouncilReviewRunner", MagicMock())
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.retry_with_fallback_models", standard_review)
    try:
        await reviewer.run()
    finally:
        council_settings.config.publish_output = original_publish_output

    resolve_config.assert_not_called()
    standard_review.assert_awaited_once()


@pytest.mark.asyncio
async def test_incremental_eligibility_gate_runs_before_council_selection(monkeypatch):
    reviewer = _reviewer_for_integration_run()
    reviewer.incremental = SimpleNamespace(is_incremental=True)
    reviewer._can_run_incremental_review = MagicMock(return_value=False)
    resolve_config = MagicMock(side_effect=AssertionError("ineligible incremental review must stop before selection"))

    monkeypatch.setattr("pr_agent.tools.pr_reviewer.resolve_council_review_config", resolve_config)

    await reviewer.run()

    reviewer._can_run_incremental_review.assert_called_once_with()
    resolve_config.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("is_auto", "is_incremental"),
    [(False, False), (True, False), (False, True)],
    ids=["manual", "automated", "incremental"],
)
async def test_pr_reviewer_runs_council_for_every_review_mode(
    monkeypatch,
    council_settings,
    is_auto,
    is_incremental,
):
    original_publish_output = council_settings.config.publish_output
    council_settings.config.publish_output = False
    reviewer = _reviewer_for_integration_run()
    reviewer.is_auto = is_auto
    reviewer.incremental = SimpleNamespace(is_incremental=is_incremental)
    reviewer._can_run_incremental_review = MagicMock(return_value=True)
    council_config = CouncilReviewConfig(enabled=True)
    council_result = SimpleNamespace(prediction=_VALID_REVIEW, metadata={"strategy": "council_review"})
    runner = MagicMock()
    runner.run = AsyncMock(return_value=council_result)
    standard_review = AsyncMock()

    monkeypatch.setattr("pr_agent.tools.pr_reviewer.extract_and_cache_pr_tickets", AsyncMock())
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.resolve_council_review_config", lambda: council_config)
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.CouncilReviewRunner", MagicMock(return_value=runner))
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.retry_with_fallback_models", standard_review)
    try:
        await reviewer.run()
    finally:
        council_settings.config.publish_output = original_publish_output

    runner.run.assert_awaited_once()
    standard_review.assert_not_awaited()
    if is_incremental:
        reviewer._can_run_incremental_review.assert_called_once_with()


@pytest.mark.asyncio
async def test_pr_reviewer_runtime_no_quorum_does_not_run_standard_review_or_publish_member_result(
    monkeypatch,
    council_settings,
):
    original_publish_output = council_settings.config.publish_output
    original_is_auto_command = council_settings.config.get("is_auto_command", False)
    council_settings.config.publish_output = True
    council_settings.config.is_auto_command = False
    reviewer = _reviewer_for_integration_run()
    council_config = CouncilReviewConfig(enabled=True)
    standard_review = AsyncMock()
    runner = MagicMock()
    runner.run = AsyncMock(side_effect=CouncilReviewError("Council Review failed: no quorum"))

    monkeypatch.setattr("pr_agent.tools.pr_reviewer.extract_and_cache_pr_tickets", AsyncMock())
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.resolve_council_review_config", lambda: council_config)
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.CouncilReviewRunner", MagicMock(return_value=runner))
    monkeypatch.setattr("pr_agent.tools.pr_reviewer.retry_with_fallback_models", standard_review)
    try:
        await reviewer.run()
    finally:
        council_settings.config.publish_output = original_publish_output
        council_settings.config.is_auto_command = original_is_auto_command

    standard_review.assert_not_awaited()
    assert reviewer.git_provider.publish_comment.call_args_list == [
        (("Preparing review...",), {"is_temporary": True}),
        (("Council Review failed: no quorum",), {}),
    ]
