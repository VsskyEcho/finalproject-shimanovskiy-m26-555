"""
Вспомогательные функции:
хранилище JSON, валидаторы, курсы валют
"""

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

# данные в папке data
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"
USERS_FILE = DATA_DIR / "users.json"

RATES_TTL_SECONDS = 300


def user_to_dict(user: User) -> dict:
    return {
        "user_id": user.user_id,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "salt": user.salt,
        "registration_date": user.registration_date.isoformat(timespec="seconds"),
    }


def user_from_dict(data: dict) -> User:
    return User(
        data["user_id"],
        data["username"],
        data["hashed_password"],
        data["salt"],
        datetime.fromisoformat(data["registration_date"]),
    )


def portfolio_to_dict(portfolio: Portfolio) -> dict:
    return {
        "user_id": portfolio.user_id,
        "wallets": {
            code: {"balance": wallet.balance}
            for code, wallet in portfolio.wallets.items()
        },
    }


def portfolio_from_dict(data: dict) -> Portfolio:
    wallets = {
        code: Wallet(code, item["balance"]) for code, item in data["wallets"].items()
    }
    return Portfolio(data["user_id"], wallets)


# загрузка и сохранение, пользователей и портфелей
def load_users() -> list[User]:
    return [user_from_dict(item) for item in DatabaseManager().read("users", [])]


def save_users(users: list[User]) -> None:
    DatabaseManager().write("users", [user_to_dict(user) for user in users])


def load_portfolios() -> list[Portfolio]:
    items = DatabaseManager().read("portfolios", [])
    return [portfolio_from_dict(item) for item in items]


def save_portfolios(portfolios: list[Portfolio]) -> None:
    data = [portfolio_to_dict(item) for item in portfolios]
    DatabaseManager().write("portfolios", data)


# валидация
def validate_currency_code(code: str) -> str:
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Код валюты не может быть пустым")
    return code.strip().upper()


def validate_amount(amount: Any) -> float:
    try:
        value = float(amount)
    except (TypeError, ValueError):
        raise ValueError("'amount' должен быть положительным числом") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    return value


# курсы валют
def load_rates_snapshot() -> dict:
    """
    Снимок курсов из rates.json
    Если файл в старом или пустом формате,
    возвращается пустой словарь
    """
    data = DatabaseManager().read("rates", {})
    if not isinstance(data, dict) or not isinstance(data.get("pairs"), dict):
        return {"pairs": {}, "last_refresh": None}
    return {"pairs": data["pairs"], "last_refresh": data.get("last_refresh")}


def _is_fresh(updated_at: str) -> bool:
    """
    True, если запись обновлена недавно
    (меньше TTL секунд назад)
    """
    ttl = SettingsLoader().get("rates_ttl_seconds")
    age = datetime.now(timezone.utc) - datetime.fromisoformat(updated_at)
    return age.total_seconds() < ttl


def _fresh_entry(code: str, pairs: dict) -> dict | None:
    """
    Свежая запись CODE_USD из снимка или None
    """
    entry = pairs.get(f"{code}_USD")
    if entry and _is_fresh(entry["updated_at"]):
        return entry
    return None


def _refresh_rates() -> None:
    """
    Пробует обновить кеш через Parser Service
    """
    # импорт здесь, чтобы ядро не тянуло сетевые зависимости при загрузке
    from valutatrade_hub.parser_service.updater import build_updater

    build_updater().run_update()


def get_rate(from_code: str, to_code: str) -> dict:
    """
    Возвращает курс обмена между двумя валютами
    """
    from_code = get_currency(from_code).code
    to_code = get_currency(to_code).code
    if from_code == to_code:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"rate": 1.0, "updated_at": stamp}

    codes = [code for code in (from_code, to_code) if code != "USD"]
    pairs = load_rates_snapshot()["pairs"]
    if any(_fresh_entry(code, pairs) is None for code in codes):
        _refresh_rates()
        pairs = load_rates_snapshot()["pairs"]

    entries: dict[str, dict] = {}
    for code in codes:
        entry = _fresh_entry(code, pairs)
        if entry is None:
            raise ApiRequestError(
                f"курс {code}→USD отсутствует или устарел. Выполните update-rates"
            )
        entries[code] = entry

    to_usd = {code: entry["rate"] for code, entry in entries.items()}
    to_usd["USD"] = 1.0
    oldest = min(entry["updated_at"] for entry in entries.values())
    return {"rate": to_usd[from_code] / to_usd[to_code], "updated_at": oldest}
