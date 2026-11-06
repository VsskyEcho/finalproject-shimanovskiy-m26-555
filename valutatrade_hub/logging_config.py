"""
Настройка логов
(формат, уровень, ротация файлов)
"""

import logging
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import SettingsLoader

LOGGER_NAME = "valutatrade"
PARSER_LOGGER_NAME = f"{LOGGER_NAME}.parser"
LOG_FORMAT = "%(levelname)s %(asctime)s %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _configure(logger_name: str, path_key: str) -> logging.Logger:
    """
    Подключаем файловый обработчик
    с ротацией и повторным вызовом
    """
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger

    settings = SettingsLoader()
    log_path = settings.get_path(path_key)
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


def setup_logging() -> logging.Logger:
    """
    Логи операций (actions.log)
    и отдельный лог парсера (parser.log)
    """
    _configure(PARSER_LOGGER_NAME, "parser_log_path")
    return _configure(LOGGER_NAME, "log_path")
