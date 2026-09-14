"""OpenAI provider adapter implementing ILLMService."""

import logging
import time
from typing import Any

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.domain.messages import CanonicalMessage, MessageRole
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMProviderError,
    LLMResponseParsingError,
    LLMTimeoutError,
)
from app.observability.events import record_llm_event

logger = logging.getLogger("app.llm.openai")


class OpenAILLMService:
    """OpenAI API adapter implementing ILLMService."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        default_timeout: float = 30.0,
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise LLMConfigurationError("OpenAI API key must not be empty.")

        self._model = model
        self._default_timeout = default_timeout
        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=default_timeout,
            base_url=base_url,
        )

    @property
    def provider_name(self) -> str:
        """Provider name identifier."""
        return "openai"

    @property
    def model_name(self) -> str:
        """Configured model name identifier."""
        return self._model

    def _convert_to_openai_messages(
        self, messages: list[CanonicalMessage]
    ) -> list[ChatCompletionMessageParam]:
        """Convert canonical domain messages to OpenAI chat completion parameters."""
        openai_messages: list[ChatCompletionMessageParam] = []
        for msg in messages:
            role = msg.role.value
            if role == MessageRole.SYSTEM.value:
                openai_messages.append({"role": "system", "content": msg.text})
            elif role == MessageRole.ASSISTANT.value:
                openai_messages.append({"role": "assistant", "content": msg.text})
            else:
                openai_messages.append({"role": "user", "content": msg.text})
        return openai_messages

    async def generate(
        self,
        messages: list[CanonicalMessage],
        *,
        timeout: float | None = None,
    ) -> CanonicalMessage:
        """Call OpenAI chat completion API asynchronously."""
        request_timeout = timeout or self._default_timeout
        formatted_messages = self._convert_to_openai_messages(messages)

        logger.debug(
            "Dispatching LLM generation to OpenAI model %s with %d messages (timeout=%.1fs)",
            self._model,
            len(messages),
            request_timeout,
        )

        start_time = time.monotonic()
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=formatted_messages,
                timeout=request_timeout,
            )
        except openai.APITimeoutError as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            record_llm_event("llm_timeout", self.provider_name, self.model_name, duration_ms, error=exc)
            logger.error("OpenAI request timed out after %.1fs: %s", request_timeout, exc)
            raise LLMTimeoutError(
                message=f"OpenAI request exceeded timeout limit of {request_timeout}s.",
                details={"model": self._model, "timeout": request_timeout},
            ) from exc
        except openai.APIStatusError as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            record_llm_event("llm_api_error", self.provider_name, self.model_name, duration_ms, error=exc)
            logger.error(
                "OpenAI returned API status error [%d]: %s",
                exc.status_code,
                exc.message,
            )
            raise LLMProviderError(
                message=f"OpenAI service error: {exc.message}",
                details={"status_code": exc.status_code, "model": self._model},
            ) from exc
        except openai.APIConnectionError as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            record_llm_event("llm_connection_error", self.provider_name, self.model_name, duration_ms, error=exc)
            logger.error("Failed to connect to OpenAI API: %s", exc)
            raise LLMProviderError(
                message="Unable to connect to OpenAI provider API.",
                details={"model": self._model},
            ) from exc
        except openai.OpenAIError as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            record_llm_event("llm_sdk_error", self.provider_name, self.model_name, duration_ms, error=exc)
            logger.error("OpenAI SDK general error: %s", exc)
            raise LLMProviderError(
                message=f"OpenAI error: {str(exc)}",
                details={"model": self._model},
            ) from exc
        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            record_llm_event("llm_unexpected_error", self.provider_name, self.model_name, duration_ms, error=exc)
            logger.error("Unexpected error during OpenAI generation: %s", exc, exc_info=True)
            raise LLMProviderError(
                message="Unexpected error during LLM generation.",
                details={"model": self._model},
            ) from exc

        duration_ms = (time.monotonic() - start_time) * 1000

        if not response.choices or not response.choices[0].message:
            raise LLMResponseParsingError(
                message="OpenAI response contained no valid choices or message content.",
                details={"response_id": response.id},
            )

        content: Any = response.choices[0].message.content
        if content is None:
            raise LLMResponseParsingError(
                message="OpenAI returned null response content.",
                details={"response_id": response.id},
            )

        input_tokens = response.usage.prompt_tokens if response.usage else None
        output_tokens = response.usage.completion_tokens if response.usage else None
        total_tokens = response.usage.total_tokens if response.usage else None

        record_llm_event(
            event="llm_generate",
            provider=self.provider_name,
            model=self.model_name,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

        return CanonicalMessage.from_text(
            text=str(content),
            role=MessageRole.ASSISTANT,
            message_id=response.id,
        )

