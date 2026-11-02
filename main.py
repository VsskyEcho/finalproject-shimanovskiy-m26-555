from valutatrade_hub.core.models import Portfolio, User

"""
Тестирование
"""

user = User.create(1, "alice", "1234")
print(user.get_user_info())
print(user.verify_password("1234"), user.verify_password("zzzz"))  # True False

p = Portfolio(user.user_id, user=user)
p.add_currency("usd").deposit(1500)
p.add_currency("btc").deposit(0.05)
p.add_currency("eur").deposit(200)
print(f"{p.get_total_value():.2f} USD")  # 4682.58 USD

wallet = p.get_wallet("BTC")
assert wallet is not None
try:
    wallet.withdraw(0.06)
except ValueError as e:
    print(e)
