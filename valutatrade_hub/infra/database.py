"""
Singleton DatabaseManager:
абстракция над JSON-хранилищем
"""

import json
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """
    Читает и пишет JSON-коллекции по имени:
    'users', 'portfolios', 'rates'

    Имя коллекции превращается в путь через настройку '<имя>_path'.
    Singleton реализован через __new__ тк. это и читабельнее,
    и проще, чем через декоратор @singleton.
    """

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> "DatabaseManager":
        """
        возвращает один и тот же экземпляр
        при повторном импорте модуля
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def _path(name: str) -> Path:
        return SettingsLoader().get_path(f"{name}_path")

    def read(self, name: str, default: Any) -> Any:
        """
        Читает коллекцию, если файла нет или он пуст,
        вернёт default
        """
        path = self._path(name)
        if not path.exists() or path.stat().st_size == 0:
            return default
        with path.open(encoding="utf-8") as file:
            return json.load(file)

    def write(self, name: str, data: Any) -> None:
        """
        Записывает коллекцию в JSON-файл
        """
        path = self._path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        tmp_path.replace(path)
