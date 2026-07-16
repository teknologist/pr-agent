from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import pr_agent.algo.ai_handlers.openai_ai_handler as openai_handler


@pytest.mark.asyncio
async def test_openai_handler_suppresses_raw_council_logging(monkeypatch):
    secret = "raw member peer ranking prompt chair output"
    response = SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=secret),
            finish_reason="stop",
        )],
        usage=SimpleNamespace(total_tokens=17),
    )
    create = AsyncMock(return_value=response)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    logger = MagicMock()
    monkeypatch.setattr(openai_handler, "AsyncOpenAI", lambda: client)
    monkeypatch.setattr(openai_handler, "get_logger", lambda: logger)
    handler = openai_handler.OpenAIHandler.__new__(openai_handler.OpenAIHandler)
    handler.suppress_raw_logging = True

    result = await handler.chat_completion(
        model="gpt-4o",
        system=f"system {secret}",
        user=f"user {secret}",
    )

    assert result == (secret, "stop")
    assert secret not in repr(logger.mock_calls)


@pytest.mark.asyncio
async def test_openai_handler_suppresses_raw_council_error_details(monkeypatch):
    secret = "raw partial council output"
    create = AsyncMock(side_effect=RuntimeError(secret))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    logger = MagicMock()
    monkeypatch.setattr(openai_handler, "AsyncOpenAI", lambda: client)
    monkeypatch.setattr(openai_handler, "get_logger", lambda: logger)
    handler = openai_handler.OpenAIHandler.__new__(openai_handler.OpenAIHandler)
    handler.suppress_raw_logging = True

    with pytest.raises(Exception):
        await handler.chat_completion(model="gpt-4o", system="system", user="user")

    assert secret not in repr(logger.mock_calls)
