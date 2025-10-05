import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.database import async_engine
from app.main import app

@pytest.mark.asyncio
async def test_radarr_import_inserts_movies(httpx_mock):
    """
    Проверяем, что ручка /import добавляет фильмы в базу
    """

    # Подделываем ответ Radarr API
    httpx_mock.add_response(
        url="http://fake-radarr.local/api/v3/movie",
        json=[
            {"id": 1, "title": "Inception", "year": 2010},
            {"id": 2, "title": "Interstellar", "year": 2014}
        ],
        status_code=200
    )

    # Устанавливаем переменные окружения для Radarr
    import os
    os.environ["RADARR_URL"] = "http://fake-radarr.local"
    os.environ["RADARR_API_KEY"] = "dummy"

    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post("/import")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "ok"
        assert data["imported"] >= 2  # число фильмов, которое вернул Radarr

    # Проверим, что фильмы реально добавились в базу
    async with async_engine.begin() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM media"))
        count = result.scalar()
        assert count >= 2, "Фильмы не были импортированы в таблицу media"