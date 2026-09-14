"""Database and persistence layer."""

from app.db.base import Base
from app.db.exceptions import (
    ConversationNotFoundError,
    PersistenceConfigurationError,
    PersistenceError,
)
from app.db.interfaces import IConversationRepository
from app.db.models.conversation import ConversationModel
from app.db.models.message import MessageModel
from app.db.repositories.conversation import SQLAlchemyConversationRepository
from app.db.session import (
    check_database_connection,
    create_async_engine_instance,
    create_session_factory,
    get_db_session,
    get_engine,
    get_session_factory,
)

__all__ = [
    "Base",
    "ConversationModel",
    "ConversationNotFoundError",
    "IConversationRepository",
    "MessageModel",
    "PersistenceConfigurationError",
    "PersistenceError",
    "SQLAlchemyConversationRepository",
    "check_database_connection",
    "create_async_engine_instance",
    "create_session_factory",
    "get_db_session",
    "get_engine",
    "get_session_factory",
]
