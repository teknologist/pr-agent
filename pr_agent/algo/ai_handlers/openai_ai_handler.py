from os import environ

import openai
from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception_type, retry_if_not_exception_type, stop_after_attempt

from pr_agent.algo.ai_handlers.base_ai_handler import (
    UNSET,
    BaseAiHandler,
    ChatCompletionResult,
    ModelInferenceSettings,
)
from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger

OPENAI_RETRIES = 5


class OpenAIHandler(BaseAiHandler):
    supports_council_redaction = True

    def __init__(self):
        # Initialize OpenAIHandler specific attributes here
        try:
            super().__init__()
            environ["OPENAI_API_KEY"] = get_settings().openai.key
            if get_settings().get("OPENAI.ORG", None):
                openai.organization = get_settings().openai.org
            if get_settings().get("OPENAI.API_TYPE", None):
                if get_settings().openai.api_type == "azure":
                    self.azure = True
                    openai.azure_key = get_settings().openai.key
            if get_settings().get("OPENAI.API_VERSION", None):
                openai.api_version = get_settings().openai.api_version
            if get_settings().get("OPENAI.API_BASE", None):
                environ["OPENAI_BASE_URL"] = get_settings().openai.api_base

        except AttributeError as e:
            raise ValueError("OpenAI key is required") from e

    @property
    def deployment_id(self):
        """
        Returns the deployment ID for the OpenAI API.
        """
        return get_settings().get("OPENAI.DEPLOYMENT_ID", None)

    @retry(
        retry=retry_if_exception_type(openai.APIError) & retry_if_not_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(OPENAI_RETRIES),
    )
    async def chat_completion(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.2,
        img_path: str = None,
        _return_metadata: bool = False,
    ):
        suppress_raw_logging = self.suppress_raw_logging
        try:
            if img_path:
                get_logger().warning(f"Image path is not supported for OpenAIHandler. Ignoring image path: {img_path}")
            if not suppress_raw_logging:
                get_logger().info("System: ", system)
                get_logger().info("User: ", user)
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            client = AsyncOpenAI()
            chat_completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            resp = chat_completion.choices[0].message.content
            finish_reason = chat_completion.choices[0].finish_reason
            usage = chat_completion.usage
            if not suppress_raw_logging:
                get_logger().info("AI response", response=resp, messages=messages, finish_reason=finish_reason,
                                  model=model, usage=usage)
            if _return_metadata:
                token_usage = {}
                for field_name in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    value = usage.get(field_name) if isinstance(usage, dict) else getattr(usage, field_name, None)
                    if isinstance(value, int) and not isinstance(value, bool):
                        token_usage[field_name] = value
                metadata = {"warnings": []}
                if token_usage:
                    metadata["token_usage"] = token_usage
                return ChatCompletionResult(resp, finish_reason, metadata)
            return resp, finish_reason
        except openai.RateLimitError as e:
            if suppress_raw_logging:
                get_logger().error("Rate limit error during LLM inference")
            else:
                get_logger().error(f"Rate limit error during LLM inference: {e}")
            raise
        except openai.APIError as e:
            if suppress_raw_logging:
                get_logger().warning("Error during LLM inference")
            else:
                get_logger().warning(f"Error during LLM inference: {e}")
            raise
        except Exception as e:
            if suppress_raw_logging:
                get_logger().warning("Unknown error during LLM inference")
            else:
                get_logger().warning(f"Unknown error during LLM inference: {e}")
            raise openai.APIError from e

    async def chat_completion_with_metadata(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float | None = None,
        img_path: str = None,
        inference_settings: ModelInferenceSettings | None = None,
    ) -> ChatCompletionResult:
        """Return an OpenAI completion plus request-scoped metadata."""
        metadata = {"warnings": []}
        effective_temperature = get_settings().config.temperature if temperature is None else temperature
        if inference_settings is not None:
            if inference_settings.temperature is not UNSET:
                effective_temperature = inference_settings.temperature
            if inference_settings.reasoning_effort is not UNSET:
                metadata["warnings"].append({
                    "code": "unsupported_inference_setting",
                    "setting": "reasoning_effort",
                    "message": "reasoning_effort override is not supported by this AI handler and was ignored.",
                })

        result = await self.chat_completion(
            model=model,
            system=system,
            user=user,
            temperature=effective_temperature,
            img_path=img_path,
            _return_metadata=True,
        )
        result.metadata["warnings"].extend(metadata["warnings"])
        return result
