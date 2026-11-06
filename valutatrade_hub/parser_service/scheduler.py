"""
Планировщик периодического обновления курсов
(фоновый поток)
"""

import logging
import threading

from valutatrade_hub.logging_config import PARSER_LOGGER_NAME
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = logging.getLogger(PARSER_LOGGER_NAME)

MIN_INTERVAL_SECONDS = 10  # защита от слишком частых запросов к API
STOP_TIMEOUT_SECONDS = 5


class RatesScheduler:
    """
    Раз в interval_seconds запускает
    RatesUpdater.run_update() в фоне
    """

    def __init__(self, updater: RatesUpdater, interval_seconds: int) -> None:
        if interval_seconds < MIN_INTERVAL_SECONDS:
            raise ValueError(
                f"Интервал должен быть не меньше {MIN_INTERVAL_SECONDS} секунд"
            )
        self._updater = updater
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def interval_seconds(self) -> int:
        return self._interval

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """
        Запускает фоновый поток
        """
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, name="rates-scheduler", daemon=True
        )
        self._thread.start()
        logger.info("Scheduler started (interval: %d s)", self._interval)

    def stop(self) -> None:
        """
        Останавливает поток
        и ждёт его завершения
        """
        thread = self._thread
        if thread is None or not thread.is_alive():
            return
        self._stop_event.set()
        thread.join(timeout=STOP_TIMEOUT_SECONDS)
        logger.info("Scheduler stopped")

    def _loop(self) -> None:
        """
        Фоновый поток
        Раз в interval_seconds вызывает RatesUpdater.run_update()
        """
        while not self._stop_event.wait(self._interval):
            try:
                self._updater.run_update()
            except Exception:
                logger.exception("Scheduled update failed")
