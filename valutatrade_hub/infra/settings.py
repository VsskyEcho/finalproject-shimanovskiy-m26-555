"""
Singleton SettingsLoader:
загрузка/кеширование конфигурации проекта
из pyproject.toml, секция [tool.valutatrade]
"""

import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

_MISSING = object()  # отличает «значение по умолчанию не задано» от None


class SettingsLoader:
    """Конфигурация проекта из pyproject.toml, секция [tool.valutatrade].

    Singleton реализован через __new__ тк. это и читабельнее,
    и проще, чем через декоратор @singleton.
    Повторный импорт модуля не создаёт второй экземпляр
    модули кешируются в sys.modules,
    а сам экземпляр создаётся лениво при первом SettingsLoader().
    """

    _instance: "SettingsLoader | None" = None
    _config: dict[str, Any]

    def __new__(cls) -> "SettingsLoader":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance.reload()
            cls._instance = instance
        return cls._instance

    def reload(self) -> None:
        """
        Перечитывает конфигурацию
        """
        config: dict[str, Any] = {}
        if PYPROJECT_PATH.exists():
            with PYPROJECT_PATH.open("rb") as file:
                section = tomllib.load(file).get("tool", {}).get("valutatrade", {})
            config.update(section)
        config.setdefault("rates_ttl_seconds", 300)
        config.setdefault("default_base_currency", "USD")
        config.setdefault("users_path", "data/users.json")
        config.setdefault("portfolios_path", "data/portfolios.json")
        config.setdefault("rates_path", "data/rates.json")
        config.setdefault("log_path", "logs/actions.log")
        config.setdefault("log_level", "INFO")
        config.setdefault("log_format", "text")
        config.setdefault("log_max_bytes", 1_000_000)
        config.setdefault("log_backup_count", 3)
        self._config = config

    def get(self, key: str, default: Any = _MISSING) -> Any:
        """
        Возвращает параметр без default
        неизвестный ключ даёт KeyError
        """
        if key in self._config:
            return self._config[key]
        if default is _MISSING:
            raise KeyError(f"Неизвестный параметр конфигурации: {key}")
        return default

    def get_path(self, key: str) -> Path:
        """
        Путь из конфигурации
        относительные пути считаются от корня проекта
        """
        path = Path(self.get(key))
        return path if path.is_absolute() else PROJECT_ROOT / path
