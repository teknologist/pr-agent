import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import pr_agent.algo.ai_handlers.litellm_ai_handler as litellm_handler
from pr_agent.algo.ai_handlers.base_ai_handler import ModelInferenceSettings


class FakeBox:
    def __init__(self, values=None, **attrs):
        self._values = values or {}
        for key, value in attrs.items():
            setattr(self, key, value)

    def get(self, key, default=None):
        return self._values.get(key, default)


class FakeSettings:
    def __init__(self, config_values=None, settings_values=None):
        self.config = FakeBox(
            config_values or {},
            reasoning_effort=None,
            temperature=0.2,
            ai_timeout=30,
            custom_reasoning_model=False,
            max_model_tokens=32000,
            verbosity_level=0,
            model="gpt-4o",
        )
        self.litellm = FakeBox()
        self._settings_values = settings_values or {}

    def get(self, key, default=None):
        return self._settings_values.get(key, default)


def _mock_response(content="ok", usage=None):
    mock = MagicMock()
    response = {"choices": [{"message": {"content": content}, "finish_reason": "stop"}]}
    mock.__getitem__.side_effect = response.__getitem__
    mock.dict.return_value = response
    mock.usage = usage
    return mock


@pytest.mark.asyncio
async def test_metadata_completion_can_suppress_raw_council_logging(monkeypatch):
    settings = FakeSettings(config_values={"seed": -1})
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: settings)
    logger = MagicMock()
    monkeypatch.setattr(litellm_handler, "get_logger", lambda: logger)

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response("raw chair output")
        handler = litellm_handler.LiteLLMAIHandler()
        handler.suppress_raw_logging = True

        await handler.chat_completion_with_metadata(
            model="gpt-4o",
            system="raw member prompt",
            user="raw peer ranking",
        )

    logged = repr(logger.mock_calls)
    assert "raw member prompt" not in logged
    assert "raw peer ranking" not in logged
    assert "raw chair output" not in logged


@pytest.mark.asyncio
async def test_metadata_completion_disables_content_callbacks_for_council(monkeypatch):
    settings = FakeSettings(config_values={"seed": -1})
    settings.litellm = FakeBox({"enable_callbacks": True})
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: settings)

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response("raw chair output")
        handler = litellm_handler.LiteLLMAIHandler()
        handler.suppress_raw_logging = True
        handler.add_litellm_callbacks = MagicMock()

        await handler.chat_completion_with_metadata(
            model="gpt-4o",
            system="raw member prompt",
            user="raw peer ranking",
        )

    handler.add_litellm_callbacks.assert_not_called()


@pytest.mark.asyncio
async def test_metadata_completion_suppresses_raw_council_error_logging(monkeypatch):
    class FakeAPIError(Exception):
        pass

    settings = FakeSettings(config_values={"seed": -1})
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: settings)
    monkeypatch.setattr(litellm_handler.openai, "APIError", FakeAPIError)
    logger = MagicMock()
    monkeypatch.setattr(litellm_handler, "get_logger", lambda: logger)
    secret = "raw member peer ranking prompt chair output"
    handler = litellm_handler.LiteLLMAIHandler()
    handler.suppress_raw_logging = True
    handler._get_completion = AsyncMock(side_effect=RuntimeError(secret))

    with pytest.raises(FakeAPIError):
        await handler.chat_completion_with_metadata(
            model="gpt-4o",
            system="raw member prompt",
            user="raw peer ranking",
        )

    assert secret not in repr(logger.mock_calls)


@pytest.mark.asyncio
async def test_metadata_completion_returns_numeric_token_usage(monkeypatch):
    settings = FakeSettings(config_values={"seed": -1})
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: settings)
    usage = SimpleNamespace(prompt_tokens=11, completion_tokens=7, total_tokens=18)

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response(usage=usage)
        handler = litellm_handler.LiteLLMAIHandler()

        result = await handler.chat_completion_with_metadata(model="gpt-4o", system="sys", user="usr")

    assert result.metadata["token_usage"] == {
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "total_tokens": 18,
    }


@pytest.mark.asyncio
async def test_chat_completion_passes_seed_when_temperature_is_zero(monkeypatch):
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: FakeSettings(config_values={"seed": 123}))

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()

        await handler.chat_completion(model="gpt-4o", system="sys", user="usr", temperature=0)

    assert mock_call.call_args.kwargs["seed"] == 123


@pytest.mark.asyncio
async def test_chat_completion_rejects_seed_for_claude_opus_4_8_default_temperature(monkeypatch):
    class FakeAPIError(Exception):
        pass

    monkeypatch.setattr(litellm_handler, "get_settings", lambda: FakeSettings(config_values={"seed": 123}))
    monkeypatch.setattr(litellm_handler.openai, "APIError", FakeAPIError)

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        handler = litellm_handler.LiteLLMAIHandler()

        with pytest.raises(FakeAPIError) as exc_info:
            await handler.chat_completion(model="claude-opus-4-8", system="sys", user="usr")

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert str(exc_info.value.__cause__) == "Seed (123) is not supported with temperature (0.2) > 0"
    mock_call.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "anthropic/claude-opus-4-8",
        "claude-opus-4-8",
        "vertex_ai/claude-opus-4-8",
        "bedrock/anthropic.claude-opus-4-8",
        "bedrock/global.anthropic.claude-opus-4-8",
        "bedrock/us.anthropic.claude-opus-4-8",
        "bedrock/eu.anthropic.claude-opus-4-8",
        "bedrock/au.anthropic.claude-opus-4-8",
        "bedrock/jp.anthropic.claude-opus-4-8",
    ],
)
async def test_chat_completion_strips_temperature_for_claude_opus_4_8(monkeypatch, model):
    monkeypatch.setattr(litellm_handler, "get_settings", FakeSettings)

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()

        await handler.chat_completion(model=model, system="sys", user="usr", temperature=0.2)

    assert "temperature" not in mock_call.call_args.kwargs


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model",
    [
        "anthropic/claude-sonnet-5",
        "claude-sonnet-5",
        "vertex_ai/claude-sonnet-5",
        "bedrock/anthropic.claude-sonnet-5",
        "bedrock/global.anthropic.claude-sonnet-5",
        "bedrock/us.anthropic.claude-sonnet-5",
        "bedrock/au.anthropic.claude-sonnet-5",
        "bedrock/eu.anthropic.claude-sonnet-5",
        "bedrock/jp.anthropic.claude-sonnet-5",
    ],
)
async def test_chat_completion_strips_temperature_for_claude_sonnet_5(monkeypatch, model):
    monkeypatch.setattr(litellm_handler, "get_settings", FakeSettings)

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()

        await handler.chat_completion(model=model, system="sys", user="usr", temperature=0.2)

    assert "temperature" not in mock_call.call_args.kwargs


@pytest.mark.asyncio
async def test_chat_completion_does_not_use_extended_thinking_for_claude_opus_4_8(monkeypatch):
    monkeypatch.setattr(
        litellm_handler,
        "get_settings",
        lambda: FakeSettings(config_values={"enable_claude_extended_thinking": True}),
    )

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()

        await handler.chat_completion(model="claude-opus-4-8", system="sys", user="usr", temperature=0.2)

    assert "thinking" not in mock_call.call_args.kwargs
    assert "max_tokens" not in mock_call.call_args.kwargs
    assert "temperature" not in mock_call.call_args.kwargs


@pytest.mark.asyncio
async def test_chat_completion_does_not_use_extended_thinking_for_claude_sonnet_5(monkeypatch):
    monkeypatch.setattr(
        litellm_handler,
        "get_settings",
        lambda: FakeSettings(config_values={"enable_claude_extended_thinking": True}),
    )

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()

        await handler.chat_completion(model="claude-sonnet-5", system="sys", user="usr", temperature=0.2)

    assert "thinking" not in mock_call.call_args.kwargs
    assert "max_tokens" not in mock_call.call_args.kwargs
    assert "temperature" not in mock_call.call_args.kwargs


@pytest.mark.asyncio
async def test_chat_completion_combines_prompts_for_user_message_only_models(monkeypatch):
    monkeypatch.setattr(litellm_handler, "get_settings", FakeSettings)

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()
        handler.user_message_only_models = ["user-only-model"]

        await handler.chat_completion(model="user-only-model", system="sys", user="usr")

    messages = mock_call.call_args.kwargs["messages"]
    assert messages == [{"role": "user", "content": "sys\n\n\nusr"}]


@pytest.mark.asyncio
async def test_get_completion_suppresses_streaming_error_details_for_council(monkeypatch):
    class FailingStream:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise RuntimeError("raw partial council output")

    logger = MagicMock()
    monkeypatch.setattr(litellm_handler, "get_logger", lambda: logger)
    handler = litellm_handler.LiteLLMAIHandler.__new__(litellm_handler.LiteLLMAIHandler)
    handler.streaming_required_models = ["streaming-model"]
    handler.suppress_raw_logging = True

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = FailingStream()
        with pytest.raises(RuntimeError, match="raw partial council output"):
            await handler._get_completion(model="streaming-model", messages=[])

    assert "raw partial council output" not in repr(logger.mock_calls)


@pytest.mark.asyncio
async def test_get_completion_uses_streaming_for_required_models():
    handler = litellm_handler.LiteLLMAIHandler.__new__(litellm_handler.LiteLLMAIHandler)
    handler.streaming_required_models = ["streaming-model"]

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call, \
            patch("pr_agent.algo.ai_handlers.litellm_ai_handler._handle_streaming_response",
                  new_callable=AsyncMock) as mock_stream:
        mock_call.return_value = "stream"
        mock_stream.return_value = ("streamed text", "stop")

        resp, finish_reason, response_obj = await handler._get_completion(
            model="streaming-model",
            messages=[],
        )

    assert mock_call.call_args.kwargs["stream"] is True
    assert resp == "streamed text"
    assert finish_reason == "stop"
    assert response_obj.dict()["choices"][0]["message"]["content"] == "streamed text"


@pytest.mark.asyncio
async def test_chat_completion_with_metadata_applies_request_scoped_overrides(monkeypatch):
    settings = FakeSettings(
        config_values={"seed": -1},
        settings_values={},
    )
    settings.config.temperature = 0.7
    settings.config.reasoning_effort = "low"
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: settings)

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()
        handler.support_reasoning_models = ["reasoning-model"]

        result = await handler.chat_completion_with_metadata(
            model="reasoning-model",
            system="sys",
            user="usr",
            inference_settings=ModelInferenceSettings(
                temperature=0.1,
                reasoning_effort="high",
            ),
        )

    assert result.response == "ok"
    assert result.finish_reason == "stop"
    assert result.metadata["warnings"] == []
    assert mock_call.call_args.kwargs["temperature"] == 0.1
    assert mock_call.call_args.kwargs["reasoning_effort"] == "high"
    assert settings.config.temperature == 0.7
    assert settings.config.reasoning_effort == "low"


@pytest.mark.asyncio
async def test_chat_completion_with_metadata_inherits_global_settings_when_overrides_omitted(monkeypatch):
    settings = FakeSettings(config_values={"seed": -1})
    settings.config.temperature = 0.6
    settings.config.reasoning_effort = "medium"
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: settings)

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()
        handler.support_reasoning_models = ["reasoning-model"]

        result = await handler.chat_completion_with_metadata(
            model="reasoning-model",
            system="sys",
            user="usr",
        )

    assert result.metadata["warnings"] == []
    assert mock_call.call_args.kwargs["temperature"] == 0.6
    assert mock_call.call_args.kwargs["reasoning_effort"] == "medium"


@pytest.mark.asyncio
async def test_chat_completion_with_metadata_warns_for_unsupported_overrides(monkeypatch):
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: FakeSettings(config_values={"seed": -1}))

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()
        handler.no_support_temperature_models = ["no-temp-model"]
        handler.support_reasoning_models = []

        result = await handler.chat_completion_with_metadata(
            model="no-temp-model",
            system="sys",
            user="usr",
            inference_settings=ModelInferenceSettings(
                temperature=0.1,
                reasoning_effort="high",
            ),
        )

    assert "temperature" not in mock_call.call_args.kwargs
    assert "reasoning_effort" not in mock_call.call_args.kwargs
    assert result.metadata["warnings"] == [
        {
            "code": "unsupported_inference_setting",
            "setting": "temperature",
            "message": "temperature override is not supported by model no-temp-model and was ignored.",
        },
        {
            "code": "unsupported_inference_setting",
            "setting": "reasoning_effort",
            "message": "reasoning_effort override is not supported by model no-temp-model and was ignored.",
        },
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["openai/o3", "openrouter/openai/o3"])
async def test_provider_prefixed_reasoning_model_uses_normalized_capabilities(monkeypatch, model):
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: FakeSettings(config_values={"seed": -1}))

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()

        result = await handler.chat_completion_with_metadata(
            model=model,
            system="sys",
            user="usr",
            inference_settings=ModelInferenceSettings(
                temperature=0.1,
                reasoning_effort="high",
            ),
        )

    assert "temperature" not in mock_call.call_args.kwargs
    assert mock_call.call_args.kwargs["reasoning_effort"] == "high"
    assert result.metadata["warnings"] == [
        {
            "code": "unsupported_inference_setting",
            "setting": "temperature",
            "message": f"temperature override is not supported by model {model} and was ignored.",
        }
    ]


@pytest.mark.asyncio
async def test_invalid_request_scoped_reasoning_effort_returns_metadata_warning(monkeypatch):
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: FakeSettings(config_values={"seed": -1}))

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()
        handler.support_reasoning_models = ["reasoning-model"]

        result = await handler.chat_completion_with_metadata(
            model="reasoning-model",
            system="sys",
            user="usr",
            inference_settings=ModelInferenceSettings(reasoning_effort="invalid"),
        )

    assert mock_call.call_args.kwargs["reasoning_effort"] == "medium"
    assert result.metadata["warnings"] == [
        {
            "code": "invalid_inference_setting",
            "setting": "reasoning_effort",
            "message": "reasoning_effort override has invalid value 'invalid' and was ignored; using default 'medium'.",
        }
    ]


@pytest.mark.asyncio
async def test_unsupported_temperature_override_does_not_trigger_seed_error(monkeypatch):
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: FakeSettings(config_values={"seed": 123}))

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()
        handler.no_support_temperature_models = ["no-temp-model"]

        result = await handler.chat_completion_with_metadata(
            model="no-temp-model",
            system="sys",
            user="usr",
            inference_settings=ModelInferenceSettings(temperature=0.1),
        )

    assert "temperature" not in mock_call.call_args.kwargs
    assert mock_call.call_args.kwargs["seed"] == 123
    assert result.response == "ok"
    assert result.metadata["warnings"] == [
        {
            "code": "unsupported_inference_setting",
            "setting": "temperature",
            "message": "temperature override is not supported by model no-temp-model and was ignored.",
        }
    ]


@pytest.mark.asyncio
async def test_claude_extended_thinking_warns_when_temperature_override_is_forced(monkeypatch):
    settings = FakeSettings(
        config_values={
            "enable_claude_extended_thinking": True,
            "extended_thinking_budget_tokens": 1024,
            "extended_thinking_max_output_tokens": 2048,
            "seed": -1,
        }
    )
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: settings)

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = _mock_response()
        handler = litellm_handler.LiteLLMAIHandler()
        handler.claude_extended_thinking_models = ["claude-thinking-model"]

        result = await handler.chat_completion_with_metadata(
            model="claude-thinking-model",
            system="sys",
            user="usr",
            inference_settings=ModelInferenceSettings(temperature=0.2),
        )

    assert mock_call.call_args.kwargs["temperature"] == 1
    assert result.metadata["warnings"] == [
        {
            "code": "unsupported_inference_setting",
            "setting": "temperature",
            "message": (
                "temperature override is not supported by model "
                "claude-thinking-model and was ignored."
            ),
        }
    ]


@pytest.mark.asyncio
async def test_concurrent_chat_completion_overrides_do_not_leak(monkeypatch):
    settings = FakeSettings(config_values={"seed": -1})
    settings.config.temperature = 0.4
    settings.config.reasoning_effort = "medium"
    monkeypatch.setattr(litellm_handler, "get_settings", lambda: settings)

    captured_kwargs = []
    both_calls_started = asyncio.Event()

    async def fake_acompletion(**kwargs):
        captured_kwargs.append(kwargs)
        if len(captured_kwargs) == 2:
            both_calls_started.set()
        await both_calls_started.wait()
        return _mock_response()

    with patch("pr_agent.algo.ai_handlers.litellm_ai_handler.acompletion", side_effect=fake_acompletion):
        handler = litellm_handler.LiteLLMAIHandler()
        handler.support_reasoning_models = ["model-a", "model-b"]

        result_a, result_b = await asyncio.gather(
            handler.chat_completion_with_metadata(
                model="model-a",
                system="sys",
                user="usr-a",
                inference_settings=ModelInferenceSettings(
                    temperature=0.1,
                    reasoning_effort="low",
                ),
            ),
            handler.chat_completion_with_metadata(
                model="model-b",
                system="sys",
                user="usr-b",
                inference_settings=ModelInferenceSettings(
                    temperature=0.9,
                    reasoning_effort="high",
                ),
            ),
        )

    calls_by_model = {kwargs["model"]: kwargs for kwargs in captured_kwargs}
    assert calls_by_model["model-a"]["temperature"] == 0.1
    assert calls_by_model["model-a"]["reasoning_effort"] == "low"
    assert calls_by_model["model-b"]["temperature"] == 0.9
    assert calls_by_model["model-b"]["reasoning_effort"] == "high"
    assert result_a.metadata["warnings"] == []
    assert result_b.metadata["warnings"] == []
    assert settings.config.temperature == 0.4
    assert settings.config.reasoning_effort == "medium"
