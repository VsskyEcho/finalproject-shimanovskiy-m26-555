"""
Клиенты внешних API
единый интерфейс получения курсов
"""

import time
from abc import ABC, abstractmethod
from typing import Any, TypeGuard

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


def _positive_number(value: Any) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


class BaseApiClient(ABC):
    """
    Общий интерфейс клиентов
    fetch_rates() -> dict[PAIR, float]
    """

    key: str
    source_name: str

    def __init__(self, config: ParserConfig) -> None:
        self._config = config
        self.last_meta: dict[str, Any] = {}

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """
        Запрашивает курсы к базовой валюте
        и возвращает их в едином формате
        """

    def pair_meta(self, pair: str) -> dict[str, Any]:
        """
        Технические данные запроса
        для записи в историю"""
        return dict(self.last_meta)

    def _get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        """
        GET-запрос с обработкой сетевых
        и HTTP-ошибок
        """
        started = time.perf_counter()
        try:
            response = requests.get(
                url, params=params, timeout=self._config.REQUEST_TIMEOUT
            )
        except requests.exceptions.Timeout:
            raise ApiRequestError(
                f"{self.source_name}: превышено время ожидания"
            ) from None
        except requests.exceptions.RequestException as error:
            # текст исходной ошибки не выводим: в URL может быть API-ключ
            name = type(error).__name__
            raise ApiRequestError(
                f"{self.source_name}: сетевая ошибка ({name})"
            ) from None

        self.last_meta = {
            "request_ms": round((time.perf_counter() - started) * 1000),
            "status_code": response.status_code,
            "etag": response.headers.get("ETag"),
        }
        if response.status_code == 429:
            raise ApiRequestError(f"{self.source_name}: превышен лимит запросов (429)")
        if response.status_code != 200:
            raise ApiRequestError(f"{self.source_name}: HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise ApiRequestError(
                f"{self.source_name}: некорректный JSON в ответе"
            ) from None


class CoinGeckoClient(BaseApiClient):
    """
    Криптовалюты CoinGecko
    (запрашиваем по ID монет, а не по кодам)"""

    key = "coingecko"
    source_name = "CoinGecko"

    def fetch_rates(self) -> dict[str, float]:
        base = self._config.BASE_CURRENCY
        ids = {
            code: self._config.CRYPTO_ID_MAP[code]
            for code in self._config.CRYPTO_CURRENCIES
        }
        data = self._get_json(
            self._config.COINGECKO_URL,
            params={"ids": ",".join(ids.values()), "vs_currencies": base.lower()},
        )
        if not isinstance(data, dict):
            raise ApiRequestError(f"{self.source_name}: неожиданный формат ответа")

        rates: dict[str, float] = {}
        for code, raw_id in ids.items():
            entry = data.get(raw_id)
            value = entry.get(base.lower()) if isinstance(entry, dict) else None
            if not _positive_number(value):
                raise ApiRequestError(
                    f"{self.source_name}: нет корректного курса {code}"
                )
            rates[f"{code}_{base}"] = float(value)
        return rates

    def pair_meta(self, pair: str) -> dict[str, Any]:
        meta = super().pair_meta(pair)
        meta["raw_id"] = self._config.CRYPTO_ID_MAP.get(pair.split("_")[0])
        return meta


class ExchangeRateApiClient(BaseApiClient):
    """
    Фиатные валюты
    ExchangeRate-API (ключ подставляется в URL)"""

    key = "exchangerate"
    source_name = "ExchangeRate-API"

    def fetch_rates(self) -> dict[str, float]:
        api_key = self._config.EXCHANGERATE_API_KEY
        if not api_key:
            raise ApiRequestError(
                f"{self.source_name}: не задана переменная EXCHANGERATE_API_KEY"
            )
        base = self._config.BASE_CURRENCY
        data = self._get_json(
            f"{self._config.EXCHANGERATE_API_URL}/{api_key}/latest/{base}"
        )
        if not isinstance(data, dict) or data.get("result") != "success":
            reason = (
                data.get("error-type", "unknown-error")
                if isinstance(data, dict)
                else "bad-format"
            )
            raise ApiRequestError(f"{self.source_name}: {reason}")

        # в тз сказано брать rates,  но api возвращает conversion_rates
        api_rates = data.get("conversion_rates") or data.get("rates")
        if not isinstance(api_rates, dict):
            raise ApiRequestError(f"{self.source_name}: в ответе нет блока rates")

        rates: dict[str, float] = {}
        for code in self._config.FIAT_CURRENCIES:
            value = api_rates.get(code)
            if not _positive_number(value):
                raise ApiRequestError(
                    f"{self.source_name}: нет корректного курса {code}"
                )
            rates[f"{code}_{base}"] = round(1 / value, 8)
        return rates
