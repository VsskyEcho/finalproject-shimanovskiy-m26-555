"""
Вспомогательные функции:
хранилище JSON, валидаторы, курсы валют
"""

import math
from datetime import datetime
from pathlib import Path
from typing import Any

from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

# данные в папке data
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"
USERS_FILE = DATA_DIR / "users.json"

RATES_TTL_SECONDS = 300

STUB_RATES_TO_USD: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.0786,
    "RUB": 0.01016,
    "BTC": 59337.21,
    "ETH": 3720.0,
}


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
def _is_fresh(updated_at: str) -> bool:
    ttl = SettingsLoader().get("rates_ttl_seconds")
    age = datetime.now() - datetime.fromisoformat(updated_at)
    return age.total_seconds() < ttl


def _fetch_rate_from_stub(from_code: str, to_code: str) -> float:
    """Единственное место, которое позже заменится на Parser Service."""
    if from_code not in STUB_RATES_TO_USD or to_code not in STUB_RATES_TO_USD:
        raise ValueError(f"Не удалось получить курс для {from_code}→{to_code}")
    return STUB_RATES_TO_USD[from_code] / STUB_RATES_TO_USD[to_code]


def get_rate(from_code: str, to_code: str) -> dict:
    """
    Возвращает курс обмена между двумя валютами
    """
    from_code = validate_currency_code(from_code)
    to_code = validate_currency_code(to_code)
    now = datetime.now().isoformat(timespec="seconds")

    if from_code == to_code:
        return {"rate": 1.0, "updated_at": now}

    database = DatabaseManager()
    cache = database.read("rates", {})
    key = f"{from_code}_{to_code}"
    cached = cache.get(key)
    if cached and _is_fresh(cached["updated_at"]):
        return cached

    rate = _fetch_rate_from_stub(from_code, to_code)
    cache[key] = {"rate": rate, "updated_at": now}
    cache["source"] = "Stub"
    cache["last_refresh"] = now
    database.write("rates", cache)
    return cache[key]
