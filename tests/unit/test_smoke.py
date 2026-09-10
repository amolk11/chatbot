"""Initial smoke and foundational unit tests."""

import logging

from fastapi import FastAPI

from app.core.config import Settings
from app.core.constants import AppEnvironment
from app.core.exceptions import ChatbotError, ConfigurationError, ValidationError
from app.core.logging import SensitiveDataFilter, setup_logging


def test_project_package_imports() -> None:
    """Verify that all core architectural packages can be imported without side effects."""
    import app
    import app.api
    import app.cache
    import app.core
    import app.db
    import app.domain
    import app.graph
    import app.llm
    import app.observability
    import app.schemas
    import app.services

    assert app.__version__ == "0.1.0"
    assert app.core is not None
    assert app.api is not None
    assert app.domain is not None
    assert app.graph is not None
    assert app.llm is not None
    assert app.services is not None
    assert app.cache is not None
    assert app.db is not None
    assert app.schemas is not None
    assert app.observability is not None


def test_settings_initialization(test_settings: Settings) -> None:
    """Verify settings properties and environment predicates."""
    assert test_settings.app_name == "AI Chatbot Test"
    assert test_settings.app_env == AppEnvironment.TESTING
    assert test_settings.is_testing is True
    assert test_settings.is_development is False
    assert test_settings.is_production is False


def test_exception_hierarchy() -> None:
    """Verify custom exception representation and status code mappings."""
    base_err = ChatbotError("Something went wrong", code="GENERIC_ERROR", status_code=500)
    assert base_err.status_code == 500
    assert base_err.to_dict()["error"]["code"] == "GENERIC_ERROR"

    val_err = ValidationError("Field missing", details={"field": "query"})
    assert val_err.status_code == 422
    assert val_err.code == "VALIDATION_ERROR"
    assert val_err.details == {"field": "query"}

    cfg_err = ConfigurationError("Missing key")
    assert cfg_err.status_code == 500
    assert cfg_err.code == "CONFIGURATION_ERROR"


def test_sensitive_data_filter_redaction() -> None:
    """Verify that sensitive API keys and tokens are redacted from log messages."""
    filter_instance = SensitiveDataFilter()

    # Test OpenAI API key scrubbing
    record_openai = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Calling OpenAI with key sk-1234567890abcdefghijklmnopqrstuvwxyz",
        args=(),
        exc_info=None,
    )
    filter_instance.filter(record_openai)
    assert "sk-1234567890abcdefghijklmnopqrstuvwxyz" not in record_openai.msg
    assert "[REDACTED]" in record_openai.msg

    # Test LangSmith API key scrubbing
    record_langsmith = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="LangSmith tracing initialized with key lsv2_pt_12345678901234567890",
        args=(),
        exc_info=None,
    )
    filter_instance.filter(record_langsmith)
    assert "lsv2_pt_12345678901234567890" not in record_langsmith.msg
    assert "[REDACTED]" in record_langsmith.msg


def test_setup_logging_initialization(test_settings: Settings) -> None:
    """Verify setup_logging configures root logger without error."""
    setup_logging(test_settings)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) > 0


def test_app_factory_initialization(test_app: FastAPI, test_settings: Settings) -> None:
    """Verify application factory sets up title, version, and app state."""
    assert test_app.title == test_settings.app_name
    assert test_app.version == test_settings.app_version
    assert test_app.state.settings == test_settings
