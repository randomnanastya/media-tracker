import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("media_tracker")
    if not logger.handlers:  # Prevent duplicate handlers
        LOG_DIR = Path("/app/logs")
        LOG_DIR.mkdir(exist_ok=True)
        logger.setLevel(logging.INFO)  # Set to DEBUG for more verbosity if needed
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        file_handler = RotatingFileHandler(
            LOG_DIR / "media_tracker.log",
            maxBytes=10_000_000,  # 10MB
            backupCount=3,  # Keep 3 backup files
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


logger: logging.Logger = setup_logging()
