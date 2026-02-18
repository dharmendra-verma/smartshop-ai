"""Logging configuration for SmartShop AI."""

import logging
import sys
from app.core.config import get_settings


def setup_logging() -> None:
    """Configure application-wide logging."""
    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Quieten noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info("Logging configured at level: %s", settings.LOG_LEVEL)
