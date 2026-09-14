"""Deterministic Mock LLM service for testing and offline development."""

from app.domain.messages import CanonicalMessage, MessageRole
from app.llm.exceptions import LLMError


class MockLLMService:
    """Mock implementation of ILLMService producing deterministic responses."""

    def __init__(
        self,
        default_response: str = "This is a deterministic mock assistant response.",
        should_fail: bool = False,
        failure_exception: LLMError | None = None,
    ) -> None:
        self.default_response = default_response
        self.should_fail = should_fail
        self.failure_exception = failure_exception
        self.recorded_calls: list[list[CanonicalMessage]] = []

    async def generate(
        self,
        messages: list[CanonicalMessage],
        *,
        timeout: float | None = None,
    ) -> CanonicalMessage:
        """Simulate generation, recording received messages."""
        del timeout  # Protocol compliance; unused in mock
        self.recorded_calls.append(messages)

        if self.should_fail:
            if self.failure_exception:
                raise self.failure_exception
            raise LLMError("Simulated mock LLM failure")

        # Extract last user message text to provide contextual echo if applicable
        last_message = messages[-1] if messages else None
        last_text = last_message.text if last_message else ""

        if "echo:" in last_text.lower():
            echo_content = last_text.split("echo:", 1)[1].strip()
            response_text = f"Echo: {echo_content}"
        else:
            response_text = self.default_response

        return CanonicalMessage.from_text(
            text=response_text,
            role=MessageRole.ASSISTANT,
        )
