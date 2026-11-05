"""
Иерархия валют (наследование и полиморфизм)
и реестр валют
"""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


def _require_text(value: str, message: str) -> str:
    """
    Проверка, что значение является непустой строкой
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(message)
    return value.strip()

class Currency(ABC):
    """
    Базовая валюта: 
    человекочитаемое имя и код (тикер)
    """

    def __init__(self, name: str, code: str) -> None:
        self.name = _require_text(name, 'Название валюты не может быть пустым')
        if not (
            isinstance(code, str)
            and 2 <= len(code) <= 5
            and code.isalnum()
            and code == code.upper()
        ):
            raise ValueError(
                'Код валюты должен быть в верхнем регистре, '
                'длиной 2-5 символов, без пробелов'
            )
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """
        Строка для UI и логов
        """

class FiatCurrency(Currency):
    """
    Фиатная валюта
    с указанием страны или зоны эмиссии
    """

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        super().__init__(name, code)
        self.issuing_country = _require_text(
            issuing_country, 'Страна эмиссии не может быть пустой'
        )

    def get_display_info(self) -> str:
        return (
            f'[FIAT] {self.code} — {self.name} '
            f'(Issuing: {self.issuing_country})'
        )


class CryptoCurrency(Currency):
    """
    Криптовалюта: 
    алгоритм и последняя известная капитализация
    """

    def __init__(
        self, 
        name: str,
        code: str,
        algorithm: str,
        market_cap: float
    ) -> None:
        super().__init__(name, code)
        self.algorithm = _require_text(algorithm, 'Алгоритм не может быть пустым')
        if isinstance(market_cap, bool) or not isinstance(market_cap, (int, float)):
            raise TypeError('Капитализация должна быть числом')
        if market_cap < 0:
            raise ValueError('Капитализация не может быть отрицательной')
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        mcap = f'{self.market_cap:.2e}'.replace('e+', 'e')
        return (
            f'[CRYPTO] {self.code} — {self.name} '
            f'(Algo: {self.algorithm}, MCAP: {mcap})'
        )


# реестр валют
_CURRENCIES: dict[str, Currency] = {
    currency.code: currency
    for currency in (
        FiatCurrency('US Dollar', 'USD', 'United States'),
        FiatCurrency('Euro', 'EUR', 'Eurozone'),
        FiatCurrency('Russian Ruble', 'RUB', 'Russia'),
        CryptoCurrency('Bitcoin', 'BTC', 'SHA-256', 1.12e12),
        CryptoCurrency('Ethereum', 'ETH', 'Ethash', 4.5e11),
    )
}


def get_currency(code: str) -> Currency:
    """
    Возвращает валюту по её коду
    """
    if not isinstance(code, str) or not code.strip():
        raise ValueError('Код валюты не может быть пустым')
    normalized = code.strip().upper()
    try:
        return _CURRENCIES[normalized]
    except KeyError:
        raise CurrencyNotFoundError(normalized) from None


def get_all_currencies() -> list[Currency]:
    return list(_CURRENCIES.values())


def supported_codes() -> list[str]:
    return sorted(_CURRENCIES)