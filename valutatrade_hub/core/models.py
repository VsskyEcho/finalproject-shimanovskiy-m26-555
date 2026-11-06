"""
Классы моделей: User, Wallet, Portfolio
"""

import hashlib
import secrets
from datetime import datetime

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import InsufficientFundsError

# заглушка
EXCHANGE_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.0786,
    "RUB": 0.01016,
    "BTC": 59337.21,
    "ETH": 3720.0,
}


class User:
    """
    Пользователь системы
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    @staticmethod
    def _validate_password(password: str) -> None:
        if not isinstance(password, str) or len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """
        Внутренний метод для создания SHA-256 хеша
        из пароля и соли
        """
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    @classmethod
    def create(cls, user_id: int, username: str, password: str) -> "User":
        """
        Создание нового пользователя
        """
        cls._validate_password(password)
        salt = secrets.token_hex(8)
        return cls(
            user_id,
            username,
            cls._hash_password(password, salt),
            salt,
            datetime.now(),
        )

    def change_password(self, new_password: str) -> None:
        self._validate_password(new_password)
        self._salt = secrets.token_hex(8)
        self._hashed_password = self._hash_password(new_password, self._salt)

    def verify_password(self, password: str) -> bool:
        """
        Проверка введеного пароля на соо-ие
        """
        return self._hashed_password == self._hash_password(password, self._salt)

    def get_user_info(self) -> dict:
        """
        Информация о пользователе без пароля
        """
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }


class Wallet:
    """
    Кошелёк пользователя
    для одной валюты
    """

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")
        self.currency_code = currency_code.strip().upper()
        self.balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    @staticmethod
    def _check_amount(amount: float) -> None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError('"amount" должен быть числом')
        if amount <= 0:
            raise ValueError('"amount" должен быть положительным числом')

    def deposit(self, amount: float) -> None:
        """
        Депозит
        """
        self._check_amount(amount)
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        """
        Проверка суммы снятия
        """
        self._check_amount(amount)
        if amount > self._balance:
            raise InsufficientFundsError(self._balance, amount, self.currency_code)
        self._balance -= amount

    def get_balance_info(self) -> str:
        """
        Информация о балансе
        """
        return f"{self.currency_code}: {self._balance:.4f}"


class Portfolio:
    """
    Все кошельки одного пользователя
    """

    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None,
    ) -> None:
        self._user_id = user_id
        self._wallets: dict[str, Wallet] = dict(wallets) if wallets else {}
        self._user = user

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        return dict(self._wallets)

    @property
    def user(self) -> User | None:
        return self._user

    def add_currency(self, currency_code: str) -> Wallet:
        """
        Добавление нового кошелёка в портфель
        (если его ещё нет)
        """
        code = get_currency(currency_code).code
        if code in self._wallets:
            raise ValueError(f"Кошелёк '{code}' уже существует")
        wallet = Wallet(code)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """
        Возврат Wallet по коду валюты
        """
        return self._wallets.get(currency_code.strip().upper())

    def get_total_value(
        self,
        base_currency: str = "USD",
        exchange_rates: dict[str, float] | None = None,
    ) -> float:
        rates = exchange_rates or EXCHANGE_RATES
        base = base_currency.strip().upper()
        if base not in rates:
            raise ValueError(f'Неизвестная базовая валюта "{base}"')
        total_usd = 0.0
        for code, wallet in self._wallets.items():
            if code not in rates:
                raise ValueError(f'Нет курса для "{code}"')
            total_usd += wallet.balance * rates[code]
        return total_usd / rates[base]
