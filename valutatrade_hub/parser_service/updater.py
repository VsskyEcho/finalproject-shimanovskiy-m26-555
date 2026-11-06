"""
Координатор обновления курсов
клиенты -> объединение -> хранилище
"""

import logging
import re
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import PARSER_LOGGER_NAME
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage

logger = logging.getLogger(PARSER_LOGGER_NAME)
PAIR_PATTERN = re.compile(r"[A-Z0-9]{2,5}_[A-Z0-9]{2,5}")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RatesUpdater:
    """
    Точка входа логики парсинга
    опрашивает клиентов и сохраняет курсы
    """

    def __init__(self, clients: Sequence[BaseApiClient], storage: RatesStorage) -> None:
        self._clients = list(clients)
        self._storage = storage

    def run_update(self, source: str | None = None) -> dict[str, Any]:
        """
        Обновляет курсы (source: 'coingecko' / 'exchangerate' / None = все)

        Падение одного клиента не останавливает остальных
        Если не получено ни одного курса,
        файлы с данными остаются нетронутыми.
        """
        clients = [c for c in self._clients if source is None or c.key == source]
        if not clients:
            raise ValueError(f"Неизвестный источник '{source}'")

        logger.info(
            "Starting rates update (sources: %s)", ", ".join(c.key for c in clients)
        )
        timestamp = _utc_timestamp()
        snapshot_pairs: dict[str, dict[str, Any]] = {}
        history: list[dict[str, Any]] = []
        report: list[dict[str, Any]] = []

        for client in clients:
            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                logger.error(
                    "Failed to fetch from %s: %s", client.source_name, error.reason
                )
                report.append(
                    {
                        "name": client.source_name,
                        "ok": False,
                        "count": 0,
                        "error": error.reason,
                    }
                )
                continue

            count = 0
            for pair, rate in rates.items():
                if not PAIR_PATTERN.fullmatch(pair):
                    logger.warning(
                        "Skipped invalid pair %r from %s", pair, client.source_name
                    )
                    continue
                from_code, to_code = pair.split("_")
                snapshot_pairs[pair] = {
                    "rate": rate,
                    "updated_at": timestamp,
                    "source": client.source_name,
                }
                history.append(
                    {
                        "id": f"{pair}_{timestamp}",
                        "from_currency": from_code,
                        "to_currency": to_code,
                        "rate": rate,
                        "timestamp": timestamp,
                        "source": client.source_name,
                        "meta": client.pair_meta(pair),
                    }
                )
                count += 1
            logger.info("Fetched from %s: OK (%d rates)", client.source_name, count)
            report.append(
                {"name": client.source_name, "ok": True, "count": count, "error": None}
            )

        written = 0
        last_refresh = None
        if snapshot_pairs:
            logger.info("Writing %d rates to storage", len(snapshot_pairs))
            self._storage.append_history(history)
            written = self._storage.update_snapshot(snapshot_pairs, timestamp)
            last_refresh = timestamp
        else:
            logger.warning("No rates received: storage left unchanged")

        has_errors = any(not item["ok"] for item in report)
        logger.info("Update finished: %d rates written, errors=%s", written, has_errors)
        return {
            "sources": report,
            "total": written,
            "last_refresh": last_refresh,
            "has_errors": has_errors,
        }


def build_updater(config: ParserConfig | None = None) -> RatesUpdater:
    """
    Собирает RatesUpdater со всеми клиентами
    и хранилищем по умолчанию
    """
    config = config or ParserConfig()
    clients = [CoinGeckoClient(config), ExchangeRateApiClient(config)]
    return RatesUpdater(clients, RatesStorage())
