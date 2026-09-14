"""Unit tests for correlation ID and request logging middleware."""

import logging

import pytest
from httpx import AsyncClient

from app.api.middleware.correlation import (
    CORRELATION_ID_HEADER,
    is_valid_correlation_id,
)


def test_is_valid_correlation_id() -> None:
    """Verify correlation ID format validator."""
    assert is_valid_correlation_id("abc-123_XYZ.456") is True
    assert is_valid_correlation_id("12345") is True
    assert is_valid_correlation_id(None) is False
    assert is_valid_correlation_id("") is False
    assert is_valid_correlation_id("a" * 65) is False  # Exceeds max length
    assert is_valid_correlation_id("bad id with spaces") is False
    assert is_valid_correlation_id("<script>alert(1)</script>") is False
    assert is_valid_correlation_id("id\nwith\rnewlines") is False


@pytest.mark.asyncio
async def test_correlation_id_generated_when_missing(async_client: AsyncClient) -> None:
    """Verify response includes a newly generated correlation ID when none is provided."""
    response = await async_client.get("/health")

    assert response.status_code == 200
    assert CORRELATION_ID_HEADER in response.headers
    corr_id = response.headers[CORRELATION_ID_HEADER]
    assert is_valid_correlation_id(corr_id) is True


@pytest.mark.asyncio
async def test_correlation_id_preserved_when_valid(async_client: AsyncClient) -> None:
    """Verify valid client-supplied correlation ID is preserved in response headers."""
    custom_id = "client-req-9988-aabb"
    response = await async_client.get("/health", headers={CORRELATION_ID_HEADER: custom_id})

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == custom_id


@pytest.mark.asyncio
async def test_correlation_id_replaced_when_invalid(async_client: AsyncClient) -> None:
    """Verify malicious or invalid client-supplied correlation ID is replaced with safe UUID."""
    malicious_id = "invalid id with spaces & <script>"
    response = await async_client.get("/health", headers={CORRELATION_ID_HEADER: malicious_id})

    assert response.status_code == 200
    assert CORRELATION_ID_HEADER in response.headers
    returned_id = response.headers[CORRELATION_ID_HEADER]
    assert returned_id != malicious_id
    assert is_valid_correlation_id(returned_id) is True


@pytest.mark.asyncio
async def test_cors_preflight_headers(async_client: AsyncClient) -> None:
    """Verify CORS preflight OPTIONS request returns appropriate CORS headers."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-Correlation-ID",
    }
    response = await async_client.options("/health", headers=headers)

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] in ["*", "http://localhost:3000"]


@pytest.mark.asyncio
async def test_request_logging_emits_log_record(
    async_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify request logging middleware produces structured log output with timing."""
    with caplog.at_level(logging.INFO, logger="app.api.request"):
        response = await async_client.get("/health")
        assert response.status_code == 200

    assert len(caplog.records) > 0
    request_records = [r for r in caplog.records if r.name == "app.api.request"]
    assert len(request_records) >= 1
    record = request_records[0]
    assert "HTTP request GET /health completed with status 200" in record.getMessage()
