import logging
from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,  # не глушим uvicorn и другие логгеры
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
    "loggers": {
        # Uvicorn & FastAPI
        "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"level": "WARNING"},
        # SQLAlchemy
        "sqlalchemy": {"level": "WARNING"},
        # APScheduler
        "apscheduler": {"level": "INFO"},
        # твои собственные модули
        "app": {"level": "INFO", "handlers": ["console"], "propagate": False},
    },
}

dictConfig(LOGGING_CONFIG)

logger = logging.getLogger("app")
