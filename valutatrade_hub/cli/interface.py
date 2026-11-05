"""
Командный интерфейс ValutaTrade Hub
"""

import argparse
import shlex
from collections.abc import Callable
from datetime import datetime

from valutatrade_hub.core import usecases
from valutatrade_hub.core.currencies import CryptoCurrency, get_currency
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import User

PROMPT = "> "
SEPARATOR_WIDTH = 33

HELP_TEXT = """Доступные команды:
  register --username <имя> --password <пароль>
  login --username <имя> --password <пароль>
  show-portfolio [--base <валюта>]
  buy --currency <код> --amount <число>
  sell --currency <код> --amount <число>
  get-rate --from <код> --to <код>
  list-currencies --список валют
  help, exit"""


def _format_balance(code: str, value: float) -> str:
    """
    Форматирует баланс в зависимости от типа валюты
    """
    if isinstance(get_currency(code), CryptoCurrency):
        return f"{value:.4f}"
    return f"{value:,.2f}"


def _format_rate(rate: float) -> str:
    """
    Форматирует курс в зависимости от его значения
    """
    if rate >= 100:
        return f"{rate:.2f}"
    if rate >= 1:
        return f"{rate:.4f}"
    return f"{rate:.8f}"


def build_parser() -> argparse.ArgumentParser:
    """
    Создает парсер командной строки
    с подкомандами и аргументами
    """
    parser = argparse.ArgumentParser(prog="", add_help=False)
    commands = parser.add_subparsers(dest="command", required=True)

    register = commands.add_parser("register", help="создать пользователя")
    register.add_argument("--username", required=True)
    register.add_argument("--password", required=True)

    login = commands.add_parser("login", help="войти в систему")
    login.add_argument("--username", required=True)
    login.add_argument("--password", required=True)

    portfolio = commands.add_parser("show-portfolio", help="показать портфель")
    portfolio.add_argument("--base", default=usecases.DEFAULT_BASE_CURRENCY)

    for name, help_text in (("buy", "купить валюту"), ("sell", "продать валюту")):
        trade = commands.add_parser(name, help=help_text)
        trade.add_argument("--currency", required=True)
        trade.add_argument("--amount", required=True)

    rate = commands.add_parser("get-rate", help="курс валюты")
    rate.add_argument("--from", dest="from_code", required=True)
    rate.add_argument("--to", dest="to_code", required=True)
    commands.add_parser("list-currencies", help="список валют")
    return parser


class CommandLineInterface:
    """
    Интерактивная консоль
    """

    def __init__(self) -> None:
        self._user: User | None = None
        self._parser = build_parser()
        self._handlers: dict[str, Callable[[argparse.Namespace], None]] = {
            "register": self._handle_register,
            "login": self._handle_login,
            "show-portfolio": self._handle_show_portfolio,
            "buy": self._handle_buy,
            "sell": self._handle_sell,
            "get-rate": self._handle_get_rate,
            "list-currencies": self._handle_list_currencies,
        }

    # основные функции
    def run(self) -> None:
        """
        Запуск интерактивной консоли
        с обработкой команд и ошибок
        """
        print("ValutaTrade Hub. Команды: help, выход: exit")
        while True:
            try:
                line = input(PROMPT).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            command = line.lower()
            if command in {"exit", "quit"}:
                break
            if command == "help":
                print(HELP_TEXT)
                continue
            self.execute(line)

    def execute(self, line: str) -> None:
        """
        Разбирает и выполняет одну команду,
        показывает понятные пользователю ошибки
        """
        try:
            tokens = shlex.split(line)
        except ValueError as error:  # например, незакрытая кавычка
            print(f"Не удалось разобрать команду: {error}")
            return
        if not tokens:
            return
        tokens[0] = tokens[0].lower()
        if tokens[0] not in self._handlers:
            print(f"Неизвестная команда '{tokens[0]}'. Введите help для списка команд")
            return
        try:
            args = self._parser.parse_args(tokens)
        except SystemExit:
            return

        try:
            self._handlers[args.command](args)
        except InsufficientFundsError as error:
            print(error)
        except CurrencyNotFoundError as error:
            print(error)
            codes = ", ".join(usecases.get_supported_codes())
            print(f"Поддерживаемые валюты: {codes}")
        except ApiRequestError as error:
            print(error)
            print("Повторите попытку позже или проверьте подключение к сети.")
        except ValueError as error:
            print(error)

    # вспомогательные функции
    def _require_login(self) -> User:
        """
        Проверяет, что пользователь вошёл в систему,
        возвращает объект User
        """
        if self._user is None:
            raise ValueError("Сначала выполните login")
        return self._user

    @staticmethod
    def _print_trade(title: str, result: dict, summary: str, value: float) -> None:
        """
        Печатает результат покупки/продажи
        """
        code, base = result["currency"], result["base"]
        rate = _format_rate(result["rate"])
        print(
            f"{title} выполнена: {result['amount']:.4f} {code} "
            f"по курсу {rate} {base}/{code}"
        )
        print("Изменения в портфеле:")
        print(f"- {code}: было {result['before']:.4f} → стало {result['after']:.4f}")
        print(f"{summary}: {value:,.2f} {base}")

    # обработчики команд
    def _handle_register(self, args: argparse.Namespace) -> None:
        """
        Регистрирует нового пользователя
        """
        user = usecases.register(args.username, args.password)
        print(
            f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}). "
            f"Войдите: login --username {user.username} --password ****"
        )

    def _handle_login(self, args: argparse.Namespace) -> None:
        """
        Вход в систему
        """
        self._user = usecases.login(args.username, args.password)
        print(f"Вы вошли как '{self._user.username}'")

    def _handle_show_portfolio(self, args: argparse.Namespace) -> None:
        user = self._require_login()
        result = usecases.show_portfolio(user.user_id, args.base)
        base = result["base"]
        if not result["rows"]:
            print(
                f"У пользователя '{user.username}' пока нет кошельков. "
                "Пример: buy --currency BTC --amount 0.05"
            )
            return
        print(f"Портфель пользователя '{user.username}' (база: {base}):")
        for row in result["rows"]:
            balance = _format_balance(row["currency"], row["balance"])
            value = _format_balance(base, row["value"])
            print(f"- {row['currency']}: {balance}  → {value} {base}")
        print("-" * SEPARATOR_WIDTH)
        print(f"ИТОГО: {_format_balance(base, result['total'])} {base}")

    def _handle_buy(self, args: argparse.Namespace) -> None:
        """
        Покупка валюты
        """
        user = self._require_login()
        result = usecases.buy(user.user_id, args.currency, args.amount)
        self._print_trade(
            "Покупка", result, "Оценочная стоимость покупки", result["cost"]
        )

    def _handle_sell(self, args: argparse.Namespace) -> None:
        """
        Продажа валюты
        """
        user = self._require_login()
        result = usecases.sell(user.user_id, args.currency, args.amount)
        self._print_trade("Продажа", result, "Оценочная выручка", result["revenue"])

    def _handle_get_rate(self, args: argparse.Namespace) -> None:
        """
        Получение курса валюты
        """
        result = usecases.get_rate(args.from_code, args.to_code)
        source, target = result["from"], result["to"]
        stamp = datetime.fromisoformat(result["updated_at"])
        print(
            f"Курс {source}→{target}: {_format_rate(result['rate'])} "
            f"(обновлено: {stamp:%Y-%m-%d %H:%M:%S})"
        )
        print(
            f"Обратный курс {target}→{source}: {_format_rate(result['reverse_rate'])}"
        )

    def _handle_list_currencies(self, args: argparse.Namespace) -> None:
        """
        Список всех поддерживаемых валют
        """
        for info in usecases.list_currencies():
            print(info)


def run_cli() -> None:
    """
    Запускает интерактивную консоль
    """
    CommandLineInterface().run()
