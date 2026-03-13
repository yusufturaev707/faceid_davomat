"""Logging configuration."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Ilova uchun logging sozlamalarini o'rnatish."""
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
    )

    # Uchinchi tomon kutubxonalar log darajasini pasaytirish
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("faceid")
