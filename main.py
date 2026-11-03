from valutatrade_hub.core import usecases
from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InsufficientFundsError,
)

user = usecases.register("alice", "1234")
print(usecases.login("alice", "1234").username)  # alice
print(usecases.buy(user.user_id, "btc", 0.05))
print(usecases.buy(user.user_id, "EUR", 200))
print(usecases.show_portfolio(user.user_id))

try:
    usecases.sell(user.user_id, "BTC", 1)
except InsufficientFundsError as error:
    print(error)  # Недостаточно средств: доступно 0.0500 BTC, требуется 1.0000 BTC

print(usecases.sell(user.user_id, "BTC", 0.01))
print(usecases.get_rate("USD", "BTC"))

for action in (
    lambda: usecases.register("alice", "5555"),  # Имя пользователя 'alice' уже занято
    lambda: usecases.register("bob", "12"),  # Пароль должен быть не короче 4 символов
    lambda: usecases.login("alice", "zzzz"),  # Неверный пароль
    lambda: usecases.buy(user.user_id, "XYZ", 1),  # Неизвестная валюта 'XYZ'
    lambda: usecases.buy(
        user.user_id, "BTC", -5
    ),  # 'amount' должен быть положительным...
):
    try:
        action()
    except (ValueError, CurrencyNotFoundError) as error:
        print(error)
