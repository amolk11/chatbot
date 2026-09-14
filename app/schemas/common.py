"""Common Pydantic schemas for health, readiness, and standard API errors."""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness probe response schema."""

    status: str = Field(default="ok", description="Process health status")
    version: str = Field(..., description="Application semantic version")
    environment: str = Field(..., description="Active runtime environment")


class ReadinessResponse(BaseModel):
    """Readiness probe response schema indicating readiness to serve traffic."""

    status: str = Field(default="ready", description="Overall readiness status")
    version: str = Field(..., description="Application semantic version")
    environment: str = Field(..., description="Active runtime environment")
    checks: dict[str, str] = Field(
        default_factory=dict,
        description="Individual component readiness checks (e.g., database, redis, llm)",
    )


class ErrorDetail(BaseModel):
    """Structured error payload schema."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable safe error message")
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID associated with the request for traceability",
    )
    details: dict[str, Any] | list[Any] | None = Field(
        default=None,
        description="Optional additional validation or error context",
    )


class ErrorResponse(BaseModel):
    """Top-level error response schema conforming to API standards."""

    error: ErrorDetail = Field(..., description="Detailed error information")
