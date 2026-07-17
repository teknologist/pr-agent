"""Test configured Council Review providers without exposing credentials or response bodies."""

import asyncio

from pr_agent.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler

MODELS = {
    "OpenAI": "gpt-5.6-sol",
    "Anthropic": "anthropic/claude-opus-4-8",
    "OpenRouter": "openrouter/z-ai/glm-5.2",
}


def _unwrap(exc: BaseException) -> BaseException:
    last_attempt = getattr(exc, "last_attempt", None)
    if last_attempt:
        attempted = last_attempt.exception()
        if attempted:
            exc = attempted

    while exc.__cause__ is not None:
        exc = exc.__cause__

    return exc


async def _test(handler: LiteLLMAIHandler, provider: str, model: str) -> bool:
    try:
        await asyncio.wait_for(
            handler.chat_completion(
                model=model,
                system="Return exactly OK.",
                user="Connectivity test.",
                temperature=None,
            ),
            timeout=60,
        )
        print(f"{provider}: SUCCESS")
        return True
    except Exception as exc:
        root = _unwrap(exc)
        print(
            f"{provider}: FAILURE "
            f"type={type(root).__name__} "
            f"status={getattr(root, 'status_code', None)}"
        )
        return False


async def main() -> bool:
    handler = LiteLLMAIHandler()
    handler.enable_council_redaction()
    results = [await _test(handler, provider, model) for provider, model in MODELS.items()]
    return all(results)


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(main()) else 1)
