import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("media_tracker")
    if not logger.handlers:
        # Configurable log dir path (default /app/logs for Docker)
        log_dir_path = os.getenv("LOG_DIR_PATH", "/app/logs")
        log_dir = Path(log_dir_path)

        if os.getenv("APP_ENV") == "development" and log_dir.parent.exists():
            log_dir.mkdir(exist_ok=True)
            # Use file handler with rotation
            formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler = RotatingFileHandler(
                log_dir / "media_tracker.log", maxBytes=10_000_000, backupCount=3  # 10MB
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        else:
            # In CI or non-dev, log only to console (pytest captures stdout)
            logger.warning("Skipping file logging (not in development env or dir not available)")

        # Always add console handler for stdout (visible in docker logs or pytest)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logger.setLevel(logging.INFO)

    return logger


logger = setup_logging()
