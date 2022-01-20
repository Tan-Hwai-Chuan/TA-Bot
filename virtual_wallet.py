def init_wallet(wallet):
    wallet['Capital'] = 1000.0
    wallet['IN_POSITION'] = False
    wallet['total_trade'] = 0
    wallet['win_trade'] = 0
    wallet['lose_trade'] = 0

def buy_crypto(wallet, amount, price, fees):
    wallet['Capital'] = wallet['Capital'] - (amount * price) - fees

def sell_crypto(wallet, amount, price, fees):
    wallet['Capital'] = wallet['Capital'] + (amount * price) - fees