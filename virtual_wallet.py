import pandas as pd

def init_wallet(wallet):
    wallet['Capital'] = 1000.0
    wallet['IN_POSITION'] = False
    wallet['total_trade'] = 0
    wallet['win_trade'] = 0
    wallet['lose_trade'] = 0
    wallet['COIN'] = ""
    wallet['ASSET_WORTH'] = 0.0

def buy_crypto(wallet, amount, price, fees):
    wallet['Capital'] = wallet['Capital'] - (amount * price) - fees

def sell_crypto(wallet, amount, price, fees):
    wallet['Capital'] = wallet['Capital'] + (amount * price) - fees

def createFrame_wallet(msg):
    df = pd.DataFrame([msg])
    df = df.loc[:,['Capital','IN_POSITION','total_trade','win_trade','lose_trade','COIN','ASSET_WORTH']]
    df.columns = ['Capital','IN_POSITION','total_trade','win_trade','lose_trade','COIN','ASSET_WORTH']
    return df