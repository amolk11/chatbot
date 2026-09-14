"""Chat orchestration service executing LangGraph workflows with persisted conversation history and Redis caching."""

import logging
import time
import uuid
from typing import TYPE_CHECKING

from app.cache.exceptions import CacheError
from app.cache.interfaces import ICache
from app.cache.keys import build_chat_cache_key
from app.cache.serialization import deserialize_cached_response, serialize_cached_response
from app.core.exceptions import ValidationError
from app.core.logging import conversation_id_ctx, correlation_id_ctx
from app.db.exceptions import ConversationNotFoundError
from app.db.interfaces import IConversationRepository
from app.domain.messages import CanonicalMessage, MessageRole
from app.graph.chatbot import build_chat_graph
from app.llm.interfaces import ILLMService
from app.observability.events import record_cache_event, record_persistence_event
from app.observability.tracing import build_langgraph_trace_config

if TYPE_CHECKING:
    from app.graph.state import ChatGraphState

logger = logging.getLogger("app.services.chat")


class ChatService:
    """Application service for orchestrating conversational interactions with durable history and caching."""

    def __init__(
        self,
        llm_service: ILLMService,
        conversation_repository: IConversationRepository,
        cache: ICache | None = None,
        cache_enabled: bool = False,
        cache_ttl_seconds: int = 3600,
        max_history_messages: int = 50,
    ) -> None:
        self._llm_service = llm_service
        self._repository = conversation_repository
        self._cache = cache
        self._cache_enabled = cache_enabled
        self._cache_ttl_seconds = cache_ttl_seconds
        self._max_history_messages = max_history_messages
        self._graph = build_chat_graph(llm_service)

    async def process_message(
        self,
        message: str,
        conversation_id: str | None = None,
        correlation_id: str | None = None,
    ) -> tuple[CanonicalMessage, str]:
        """Execute chat interaction through historical context loading, caching, and LangGraph workflow.

        Args:
            message: User input text string.
            conversation_id: Optional existing conversation identifier.
            correlation_id: Optional correlation ID for tracing context.

        Returns:
            Tuple of (CanonicalMessage response, active conversation_id).

        Raises:
            ValidationError: If input message validation fails.
            ConversationNotFoundError: If supplied conversation_id does not exist.
            LLMError: If downstream LLM generation fails.
            PersistenceError: If database operations fail.
        """
        if not message or not message.strip():
            raise ValidationError("Chat input message cannot be empty or whitespace.")

        active_corr_id = correlation_id or correlation_id_ctx.get()

        # 1. Resolve active conversation ID and load existing chronological history
        if conversation_id:
            persist_start = time.monotonic()
            try:
                exists = await self._repository.conversation_exists(conversation_id)
                if not exists:
                    logger.warning("Conversation %s requested but does not exist", conversation_id)
                    raise ConversationNotFoundError(
                        message=f"Conversation '{conversation_id}' was not found.",
                        conversation_id=conversation_id,
                    )
                active_conv_id = conversation_id
                history = await self._repository.get_history(
                    active_conv_id,
                    limit=self._max_history_messages,
                )
                persist_duration = (time.monotonic() - persist_start) * 1000
                record_persistence_event(
                    event="history_loaded",
                    conversation_id=active_conv_id,
                    message_count=len(history),
                    duration_ms=persist_duration,
                )
            except ConversationNotFoundError:
                raise
            except Exception as exc:
                persist_duration = (time.monotonic() - persist_start) * 1000
                record_persistence_event(
                    event="history_load_error",
                    conversation_id=conversation_id,
                    duration_ms=persist_duration,
                    error=exc,
                )
                raise
        else:
            active_conv_id = str(uuid.uuid4())
            history = []

        conv_token = conversation_id_ctx.set(active_conv_id)
        try:
            # 2. Construct canonical user message
            user_message = CanonicalMessage.from_text(
                text=message.strip(),
                role=MessageRole.USER,
            )

            # 3. Cache lookup (if caching enabled)
            cache_key: str | None = None
            if self._cache_enabled and self._cache is not None:
                cache_start = time.monotonic()
                try:
                    cache_key = build_chat_cache_key(
                        conversation_id=active_conv_id,
                        history=history,
                        current_user_message=user_message,
                        provider=getattr(self._llm_service, "provider_name", "default"),
                        model=getattr(self._llm_service, "model_name", "default"),
                    )

                    raw_cached = await self._cache.get(cache_key)
                    cache_duration = (time.monotonic() - cache_start) * 1000

                    if raw_cached is not None:
                        try:
                            cached_response = deserialize_cached_response(raw_cached)
                            record_cache_event(
                                event="cache_hit",
                                conversation_id=active_conv_id,
                                cache_key_hash=cache_key,
                                duration_ms=cache_duration,
                            )
                            logger.info(
                                "Cache HIT for key=%s (conversation_id=%s)",
                                cache_key,
                                active_conv_id,
                            )

                            # Durably persist the turn (user + cached assistant response)
                            turn_start = time.monotonic()
                            await self._repository.persist_turn(
                                conversation_id=active_conv_id,
                                user_message=user_message,
                                assistant_message=cached_response,
                            )
                            turn_duration = (time.monotonic() - turn_start) * 1000
                            record_persistence_event(
                                event="turn_persisted",
                                conversation_id=active_conv_id,
                                message_count=2,
                                duration_ms=turn_duration,
                            )
                            return cached_response, active_conv_id
                        except CacheError as exc:
                            record_cache_event(
                                event="cache_deserialization_error",
                                conversation_id=active_conv_id,
                                cache_key_hash=cache_key,
                                error=exc,
                            )
                            logger.warning(
                                "Cache payload deserialization failed for key=%s: %s (treating as cache MISS)",
                                cache_key,
                                exc,
                            )
                    else:
                        record_cache_event(
                            event="cache_miss",
                            conversation_id=active_conv_id,
                            cache_key_hash=cache_key,
                            duration_ms=cache_duration,
                        )
                        logger.debug(
                            "Cache MISS for key=%s (conversation_id=%s)", cache_key, active_conv_id
                        )
                except Exception as exc:
                    record_cache_event(
                        event="cache_lookup_error",
                        conversation_id=active_conv_id,
                        cache_key_hash=cache_key,
                        error=exc,
                    )
                    logger.warning(
                        "Cache lookup encountered non-fatal error: %s (falling back to normal LLM generation)",
                        exc,
                    )

            # 4. Assemble full conversational context for LLM: historical turns + current user message
            graph_messages = [*history, user_message]

            initial_state: ChatGraphState = {
                "messages": graph_messages,
                "response": None,
                "error": None,
            }

            logger.info(
                "Executing chat workflow for message id=%s in conversation id=%s (history_len=%d)",
                user_message.id,
                active_conv_id,
                len(history),
            )

            # 5. Build distributed tracing configuration and invoke LangGraph workflow
            trace_config = build_langgraph_trace_config(
                correlation_id=active_corr_id,
                conversation_id=active_conv_id,
                provider=getattr(self._llm_service, "provider_name", "unknown"),
                model=getattr(self._llm_service, "model_name", "unknown"),
            )

            result_state = await self._graph.ainvoke(initial_state, config=trace_config)

            assistant_response: CanonicalMessage | None = result_state.get("response")
            if assistant_response is None:
                logger.error(
                    "Chat graph execution returned null response state for message id=%s",
                    user_message.id,
                )
                raise ValidationError(
                    "Workflow execution completed without producing an assistant response."
                )

            # 6. Persist the turn atomically (user + assistant)
            turn_start = time.monotonic()
            try:
                await self._repository.persist_turn(
                    conversation_id=active_conv_id,
                    user_message=user_message,
                    assistant_message=assistant_response,
                )
                turn_duration = (time.monotonic() - turn_start) * 1000
                record_persistence_event(
                    event="turn_persisted",
                    conversation_id=active_conv_id,
                    message_count=2,
                    duration_ms=turn_duration,
                )
            except Exception as exc:
                turn_duration = (time.monotonic() - turn_start) * 1000
                record_persistence_event(
                    event="turn_persistence_error",
                    conversation_id=active_conv_id,
                    duration_ms=turn_duration,
                    error=exc,
                )
                raise

            # 7. Asynchronously populate cache entry if caching is enabled
            if self._cache_enabled and self._cache is not None and cache_key is not None:
                try:
                    serialized_payload = serialize_cached_response(assistant_response)
                    await self._cache.set(
                        key=cache_key,
                        value=serialized_payload,
                        ttl=self._cache_ttl_seconds,
                    )
                    logger.debug(
                        "Populated cache for key=%s (ttl=%ds)", cache_key, self._cache_ttl_seconds
                    )
                except Exception as exc:
                    record_cache_event(
                        event="cache_write_error",
                        conversation_id=active_conv_id,
                        cache_key_hash=cache_key,
                        error=exc,
                    )
                    logger.warning(
                        "Cache write encountered non-fatal error for key=%s: %s", cache_key, exc
                    )

            logger.info(
                "Chat workflow and turn persistence completed successfully for conversation id=%s",
                active_conv_id,
            )
            return assistant_response, active_conv_id
        finally:
            conversation_id_ctx.reset(conv_token)
