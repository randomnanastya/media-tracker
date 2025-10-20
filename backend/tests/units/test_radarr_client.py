from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.client.radarr_client import fetch_radarr_movies


@pytest.mark.asyncio
async def test_fetch_radarr_movies_404_error():
    with (
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch("app.client.radarr_client.RADARR_API_KEY", "test_key"),
    ):
        mock_get.side_effect = httpx.HTTPStatusError(
            message="Not found",
            request=Mock(),
            response=Mock(status_code=404, text="Resource not found"),
        )
        with pytest.raises(ValueError) as exc_info:
            await fetch_radarr_movies()
        assert "API error: Resource not found" in str(exc_info.value)
