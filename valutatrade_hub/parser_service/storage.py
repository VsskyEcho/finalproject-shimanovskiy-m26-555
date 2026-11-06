"""
Хранилище Parser Service
"""

from typing import Any

from valutatrade_hub.infra.database import DatabaseManager

HISTORY_NAME = "exchange_rates"  # data/exchange_rates.json
SNAPSHOT_NAME = "rates"  # data/rates.json


class RatesStorage:
    """
    Чтение и запись
    exchange_rates.json (история)
    и rates.json (снимок)
    """

    def __init__(self, database: DatabaseManager | None = None) -> None:
        self._database = database or DatabaseManager()

    def append_history(self, records: list[dict[str, Any]]) -> int:
        """
        Дописывает замеры в историю,
        пропуская уже известные id
        """
        history = self._database.read(HISTORY_NAME, [])
        known_ids = {item["id"] for item in history}
        new_records = [item for item in records if item["id"] not in known_ids]
        if new_records:
            self._database.write(HISTORY_NAME, history + new_records)
        return len(new_records)

    def load_snapshot(self) -> dict[str, Any]:
        """
        Снимок курсов
        Файл в старом или пустом формате
        считается пустым"""
        data = self._database.read(SNAPSHOT_NAME, {})
        if not isinstance(data, dict) or not isinstance(data.get("pairs"), dict):
            return {"pairs": {}, "last_refresh": None}
        return {"pairs": data["pairs"], "last_refresh": data.get("last_refresh")}

    def update_snapshot(
        self, pairs: dict[str, dict[str, Any]], last_refresh: str
    ) -> int:
        """
        Обновляет пары,
        если новый updated_at свежее
        возвращает число обновлённых
        """
        pairs_now = self.load_snapshot()["pairs"]
        updated = 0
        for pair, entry in pairs.items():
            current = pairs_now.get(pair)
            if current is None or entry["updated_at"] > current.get("updated_at", ""):
                pairs_now[pair] = entry
                updated += 1
        self._database.write(
            SNAPSHOT_NAME, {"pairs": pairs_now, "last_refresh": last_refresh}
        )
        return updated
