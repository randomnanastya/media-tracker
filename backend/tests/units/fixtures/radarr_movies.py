RADARR_MOVIES_BASIC = [
    {
        "id": 1,
        "title": "Test Movie 1",
        "inCinemas": "2023-01-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 12345,
        "path": "/movies/Test Movie 1",
    },
    {
        "id": 2,
        "title": "Test Movie 2",
        "inCinemas": "2023-02-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 12346,
        "path": "/movies/Test Movie 2",
    },
    {
        "id": 3,
        "title": "Test Movie 3",
        "year": 2023,
        "tmdbId": 12347,
        "path": "/movies/Test Movie 3",
    },
]

RADARR_MOVIES_EMPTY: list[dict] = []

RADARR_MOVIES_WITH_INVALID_DATA = [
    {"id": 11, "title": "Movie without ID", "year": 2023, "tmdbId": 12349},
    {
        "title": "Movie with invalid date",
        "inCinemas": "2025-22-11T00:00:00Z",
        "year": 2025,
        "tmdbId": 12350,
    },
]

RADARR_MOVIES_WITHOUT_REQUIRE_FIELDS = [
    {"id": 11, "title": "Movie without ID", "year": 2023, "tmdbId": 12349},
    {
        "title": "Movie with invalid date",
        "inCinemas": "2025-22-11T00:00:00Z",
        "year": 2025,
    },
]

RADARR_MOVIES_WITHOUT_RADARR_ID = [
    {
        "id": 1,
        "title": "Movie with radarr id",
        "inCinemas": "2025-07-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 12348,
    },
    {
        "title": "Movie without any IDs",
        "year": 2023,
    },
]


RADARR_MOVIES_LARGE_LIST = [
    {
        "id": i,
        "title": f"Movie {i}",
        "inCinemas": f"2023-{(i % 12) + 1:02d}-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 10000 + i,
        "path": f"/movies/Movie {i}",
    }
    for i in range(1, 21)  # 20 фильмов
]

RADARR_MOVIES_WITH_SPECIAL_CHARACTERS = [
    {
        "id": 1,
        "title": "Movie with spéciål chàrs",
        "inCinemas": "2023-01-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 12350,
    },
    {
        "id": 2,
        "title": "Фильм с русскими символами",
        "inCinemas": "2023-02-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 12351,
    },
]
