from unittest.mock import Mock

import httpx
import pytest

from app.client.error_handler import handle_client_errors


@pytest.mark.asyncio
async def test_handle_client_errors_request_error():
    """Test handle_client_errors catches RequestError."""

    async def failing_func():
        raise httpx.RequestError("Network error", request=Mock())

    decorated_func = handle_client_errors(failing_func)
    with pytest.raises(ValueError) as exc_info:
        await decorated_func()
    assert "Client network error: Network error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_handle_client_errors_http_status_error():
    """Test handle_client_errors catches HTTPStatusError."""

    async def failing_func():
        raise httpx.HTTPStatusError(
            message="Bad Request",
            request=Mock(),
            response=Mock(status_code=400, text="Invalid request"),
        )

    decorated_func = handle_client_errors(failing_func)
    with pytest.raises(ValueError) as exc_info:
        await decorated_func()
    assert "API error: Invalid request" in str(exc_info.value)


@pytest.mark.asyncio
async def test_handle_client_errors_unexpected_error():
    """Test handle_client_errors catches unexpected errors."""

    async def failing_func():
        raise ValueError("Unexpected error")

    decorated_func = handle_client_errors(failing_func)
    with pytest.raises(ValueError) as exc_info:
        await decorated_func()
    assert "Unexpected error" in str(exc_info.value)
