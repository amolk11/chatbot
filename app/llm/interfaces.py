"""Provider-agnostic LLM interface protocols."""

from typing import Protocol, runtime_checkable

from app.domain.messages import CanonicalMessage


@runtime_checkable
class ILLMService(Protocol):
    """Abstract interface defining operations for language model generation."""

    async def generate(
        self,
        messages: list[CanonicalMessage],
        *,
        timeout: float | None = None,
    ) -> CanonicalMessage:
        """Generate an assistant message given a list of canonical conversation messages.

        Args:
            messages: List of CanonicalMessage objects representing the conversation history.
            timeout: Optional per-request timeout in seconds.

        Returns:
            A CanonicalMessage with role ASSISTANT.

        Raises:
            LLMError: When generation fails due to provider error, timeout, or configuration.
        """
        ...
