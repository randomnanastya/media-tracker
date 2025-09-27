RADARR_MOVIES_BASIC = [
    {
        "id": 1,
        "title": "Test Movie 1",
        "inCinemas": "2023-01-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 12345,
        "path": "/movies/Test Movie 1"
    },
    {
        "id": 2,
        "title": "Test Movie 2",
        "inCinemas": "2023-02-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 12346,
        "path": "/movies/Test Movie 2"
    },
    {
        "id": 3,
        "title": "Test Movie 3",
        "year": 2023,
        "tmdbId": 12347,
        "path": "/movies/Test Movie 3"
    }
]

RADARR_MOVIES_EMPTY = []

RADARR_MOVIES_WITH_INVALID_DATA = [
    {
        "id": 1,
        "title": "Movie with invalid date",
        "inCinemas": "invalid-date-format",
        "year": 2023,
        "tmdbId": 12348
    },
    {
        "title": "Movie without ID",  # Нет id
        "year": 2023,
        "tmdbId": 12349
    }
]

RADARR_MOVIES_LARGE_LIST = [
    {
        "id": i,
        "title": f"Movie {i}",
        "inCinemas": f"2023-{i:02d}-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 10000 + i,
        "path": f"/movies/Movie {i}"
    } for i in range(1, 21)  # 20 фильмов
]

RADARR_MOVIES_WITH_SPECIAL_CHARACTERS = [
    {
        "id": 1,
        "title": "Movie with spéciål chàrs",
        "inCinemas": "2023-01-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 12350
    },
    {
        "id": 2,
        "title": "Фильм с русскими символами",
        "inCinemas": "2023-02-01T00:00:00Z",
        "year": 2023,
        "tmdbId": 12351
    }
]
