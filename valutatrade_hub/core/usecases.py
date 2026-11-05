"""
Бизнес-логика Core Service:
регистрация, вход, портфель, сделки, курсы
"""

from valutatrade_hub.core import utils
from valutatrade_hub.core.currencies import (
    get_all_currencies,
    get_currency,
    supported_codes,
)
from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.infra.settings import SettingsLoader

# Базовая валюта
DEFAULT_BASE_CURRENCY = SettingsLoader().get("default_base_currency")


def _get_portfolio(portfolios: list[Portfolio], user_id: int) -> Portfolio:
    """
    Находит портфель пользователя в списке
    или создаёт пустой
    """
    for portfolio in portfolios:
        if portfolio.user_id == user_id:
            return portfolio
    portfolio = Portfolio(user_id)
    portfolios.append(portfolio)
    return portfolio


def register(username: str, password: str) -> User:
    """
    Регистрирует пользователя
    и создаёт ему пустой портфель
    """
    user = User.create(0, username, password)
    users = utils.load_users()
    if any(existing.username == user.username for existing in users):
        raise ValueError(f"Имя пользователя '{user.username}' уже занято")

    user_id = max((existing.user_id for existing in users), default=0) + 1
    user = User.create(user_id, user.username, password)
    users.append(user)
    utils.save_users(users)

    portfolios = utils.load_portfolios()
    portfolios.append(Portfolio(user_id))
    utils.save_portfolios(portfolios)
    return user


def login(username: str, password: str) -> User:
    """
    Проверяет логин и пароль,
    возвращает пользователя
    """
    username = username.strip()
    for user in utils.load_users():
        if user.username == username:
            if not user.verify_password(password):
                raise ValueError("Неверный пароль")
            return user
    raise ValueError(f"Пользователь '{username}' не найден")


def show_portfolio(user_id: int, base: str = DEFAULT_BASE_CURRENCY) -> dict:
    """
    Возвращает строки портфеля
    и итог в базовой валюте
    """
    try:
        base = get_currency(base).code
    except CurrencyNotFoundError as error:
        raise ValueError(f"Неизвестная базовая валюта '{error.code}'") from None

    portfolio = _get_portfolio(utils.load_portfolios(), user_id)
    wallets = portfolio.wallets
    codes = set(wallets) | {base, "USD"}
    rates_to_usd = {code: utils.get_rate(code, "USD")["rate"] for code in codes}

    rows = [
        {
            "currency": code,
            "balance": wallet.balance,
            "value": wallet.balance * rates_to_usd[code] / rates_to_usd[base],
        }
        for code, wallet in wallets.items()
    ]
    total = portfolio.get_total_value(base, rates_to_usd)
    return {"base": base, "rows": rows, "total": total}


def buy(
    user_id: int,
    currency_code: str,
    amount: float,
    base: str = DEFAULT_BASE_CURRENCY,
) -> dict:
    """
    Покупка: увеличивает баланс кошелька
    (создаёт его при необходимости)
    """
    code = get_currency(currency_code).code
    amount = utils.validate_amount(amount)
    rate = utils.get_rate(code, base)["rate"]

    portfolios = utils.load_portfolios()
    portfolio = _get_portfolio(portfolios, user_id)
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        wallet = portfolio.add_currency(code)

    before = wallet.balance
    wallet.deposit(amount)
    utils.save_portfolios(portfolios)
    return {
        "currency": code,
        "amount": amount,
        "rate": rate,
        "base": base,
        "before": before,
        "after": wallet.balance,
        "cost": amount * rate,
    }


def sell(
    user_id: int,
    currency_code: str,
    amount: float,
    base: str = DEFAULT_BASE_CURRENCY,
) -> dict:
    """
    Продажа валюты или криптовалюты
    """
    code = get_currency(currency_code).code
    amount = utils.validate_amount(amount)

    portfolios = utils.load_portfolios()
    portfolio = _get_portfolio(portfolios, user_id)
    wallet = portfolio.get_wallet(code)
    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: "
            "она создаётся автоматически при первой покупке."
        )

    rate = utils.get_rate(code, base)["rate"]
    before = wallet.balance
    wallet.withdraw(amount)
    utils.save_portfolios(portfolios)
    return {
        "currency": code,
        "amount": amount,
        "rate": rate,
        "base": base,
        "before": before,
        "after": wallet.balance,
        "revenue": amount * rate,
    }


def get_rate(from_code: str, to_code: str) -> dict:
    """
    Курс from -> to, время обновления и обратный курс
    """
    from_code = get_currency(from_code).code
    to_code = get_currency(to_code).code
    direct = utils.get_rate(from_code, to_code)
    reverse = utils.get_rate(to_code, from_code)
    return {
        "from": from_code,
        "to": to_code,
        "rate": direct["rate"],
        "updated_at": direct["updated_at"],
        "reverse_rate": reverse["rate"],
    }


def get_supported_codes() -> list[str]:
    """
    Список поддерживаемых кодов валют
    """
    return supported_codes()


def list_currencies() -> list[str]:
    """
    Описания всех валют
    для вывода в интерфейсе
    """
    return [currency.get_display_info() for currency in get_all_currencies()]
