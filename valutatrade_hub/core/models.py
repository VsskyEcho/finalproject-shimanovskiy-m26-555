"""
Классы моделей: User, Wallet, Portfolio
"""

import hashlib
import secrets
from datetime import datetime

#заглушка
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