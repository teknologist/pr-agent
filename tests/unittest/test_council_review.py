import asyncio
import copy
from types import SimpleNamespace

import pytest

from pr_agent.config_loader import get_settings
from pr_agent.tools.council_review import (
    CouncilReviewError,
    CouncilReviewRunner,
    resolve_council_review_config,
)

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
        settings.pr_council_review_prompt.system = "chair system"
        settings.pr_council_review_prompt.user = "chair user {{ member_reviews }}"
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


class FakeAiHandler:
    responses_by_model = {}
    calls = []
    active_calls = 0
    max_active_calls = 0

    def __init__(self):
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
        FakeAiHandler.calls.append({
            "model": model,
            "system": system,
            "user": user,
            "inference_settings": inference_settings,
        })
        FakeAiHandler.active_calls += 1
        FakeAiHandler.max_active_calls = max(FakeAiHandler.max_active_calls, FakeAiHandler.active_calls)
        await asyncio.sleep(0.01)
        FakeAiHandler.active_calls -= 1
        response = FakeAiHandler.responses_by_model[model]
        return SimpleNamespace(response=response, finish_reason="stop", metadata={"warnings": []})


def _reset_fake_handler(responses_by_model):
    FakeAiHandler.responses_by_model = responses_by_model
    FakeAiHandler.calls = []
    FakeAiHandler.active_calls = 0
    FakeAiHandler.max_active_calls = 0


def _runner(config):
    return CouncilReviewRunner(
        config=config,
        git_provider=SimpleNamespace(),
        token_handler=SimpleNamespace(),
        vars=_base_vars(),
        ai_handler_factory=FakeAiHandler,
        main_language="Python",
    )


def test_successful_council_uses_member_models_model_specific_diffs_and_returns_metadata(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
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

    assert result.prediction == _VALID_REVIEW
    assert result.metadata["strategy"] == "council_review"
    assert result.metadata["successful_member_count"] == 2
    assert diff_models == ["member-a", "member-b"]
    assert FakeAiHandler.max_active_calls > 1
    assert [call["model"] for call in FakeAiHandler.calls] == ["member-a", "member-b", "chair"]
    assert "diff-for-member-a" in FakeAiHandler.calls[0]["user"]
    assert "diff-for-member-b" in FakeAiHandler.calls[1]["user"]
    assert "raw diff" not in FakeAiHandler.calls[-1]["user"]


@pytest.mark.parametrize(
    ("source_diff", "member_review", "secret_text"),
    [
        ("raw diff with secret line", _VALID_REVIEW_WITH_FINDING, "raw diff with secret line"),
        ("+secret", _VALID_REVIEW_WITH_SHORT_DIFF_FINDING, "secret"),
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
    assert chair_call["user"].count("Member Review") == 2
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
  key_issues_to_review: []
  security_concerns: |
    No
  raw_pr_diff: |
    raw diff
""",
    ],
)
def test_structurally_invalid_member_does_not_count_toward_quorum(monkeypatch, council_settings, invalid_review):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({"member-a": invalid_review, "member-b": _VALID_REVIEW, "chair": _VALID_REVIEW})

    with pytest.raises(CouncilReviewError, match="fewer than two"):
        asyncio.run(_runner(config).run())

    assert [call["model"] for call in FakeAiHandler.calls] == ["member-a", "member-b"]


def test_numeric_and_boolean_standard_review_scalars_are_normalized(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
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

    assert result.metadata["successful_member_count"] == 2


def test_optional_prompt_fields_are_required_when_enabled(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
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


def test_no_quorum_raises_without_chair_or_standard_review_fallback(monkeypatch, council_settings):
    council_settings.set("pr_council_review", {
        "enabled": True,
        "members": [{"model": "member-a"}, {"model": "member-b"}],
        "chair": {"model": "chair"},
    })
    config = resolve_council_review_config()
    monkeypatch.setattr("pr_agent.tools.council_review.get_pr_diff", lambda *args, **kwargs: "raw diff")
    _reset_fake_handler({"member-a": _VALID_REVIEW, "member-b": "not yaml: [", "chair": _VALID_REVIEW})

    with pytest.raises(CouncilReviewError, match="fewer than two"):
        asyncio.run(_runner(config).run())

    assert [call["model"] for call in FakeAiHandler.calls] == ["member-a", "member-b"]
