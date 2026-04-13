from __future__ import annotations

import sys

from loguru import logger as loguru_logger

from src.core.config import settings


def _configure_logger() -> "loguru_logger.__class__":
    loguru_logger.remove()

    log_format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    loguru_logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.debug else settings.log_level,
        colorize=True,
    )

    return loguru_logger


logger = _configure_logger()