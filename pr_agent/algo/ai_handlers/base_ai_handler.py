from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class _UnsetInferenceSetting:
    pass


UNSET = _UnsetInferenceSetting()


@dataclass(frozen=True)
class ModelInferenceSettings:
    temperature: float | _UnsetInferenceSetting = UNSET
    reasoning_effort: str | _UnsetInferenceSetting = UNSET


@dataclass(frozen=True)
class ChatCompletionResult:
    response: str
    finish_reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAiHandler(ABC):
    """
    This class defines the interface for an AI handler to be used by the PR Agents.
    """

    manages_ai_timeout = False
    supports_council_redaction = False
    suppress_raw_logging = False

    def enable_council_redaction(self) -> bool:
        """Enable request-content redaction when this handler can guarantee it."""
        if not self.supports_council_redaction:
            return False
        self.suppress_raw_logging = True
        return True

    @abstractmethod
    def __init__(self):
        pass

    @property
    @abstractmethod
    def deployment_id(self):
        pass

    @abstractmethod
    async def chat_completion(self, model: str, system: str, user: str, temperature: float = 0.2, img_path: str = None):
        """
        This method should be implemented to return a chat completion from the AI model.
        Args:
            model (str): the name of the model to use for the chat completion
            system (str): the system message string to use for the chat completion
            user (str): the user message string to use for the chat completion
            temperature (float): the temperature to use for the chat completion
        """
        pass

    async def chat_completion_with_metadata(
        self,
        model: str,
        system: str,
        user: str,
        temperature: float | None = None,
        img_path: str = None,
        inference_settings: ModelInferenceSettings | None = None,
    ) -> ChatCompletionResult:
        """Return a chat completion plus per-call metadata for request-scoped inference settings."""
        from pr_agent.config_loader import get_settings

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

        response, finish_reason = await self.chat_completion(
            model=model,
            system=system,
            user=user,
            temperature=effective_temperature,
            img_path=img_path,
        )
        return ChatCompletionResult(response=response, finish_reason=finish_reason, metadata=metadata)
