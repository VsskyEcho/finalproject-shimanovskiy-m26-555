"""
Настройка логов
(формат, уровень, ротация файлов)
"""

import logging
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader

LOGGER_NAME = "valutatrade"
LOG_FORMAT = "%(levelname)s %(asctime)s %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging() -> logging.Logger:
    """
    Настройка логирования для приложения
    с ротацией файлов
    """
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    settings = SettingsLoader()
    log_path = settings.get_path("log_path")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.get("log_max_bytes"),
        backupCount=settings.get("log_backup_count"),
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(settings.get("log_level"))
    logger.propagate = False
    return logger
