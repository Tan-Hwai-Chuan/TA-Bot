import websocket, json, time
import sqlalchemy as sql
import pandas as pd
import config
import winsound
from datetime import datetime
from binance.client import Client
from binance.enums import *

TRADE_QUANTITY = 0.05

SOCKET ="wss://stream.binance.com:9443/ws/!ticker@arr"
PERCENT_INCREASE = 1.50
TIME_PERIOD = 299

client = Client(config.API_KEY, config.API_SECRET)

engine = sql.create_engine('sqlite:///PumpedCrypto.db')

allCrypto = {}
pumpedCryptoDict = {}
pumpedCrypto = []
oneMinCounter = 0
twoMinCounter = 0

# def setSocket():
#     global socket, trade_symbol
#     trade_symbol = input()
#     socket ="wss://stream.binance.com:9443/ws/" + trade_symbol + "@ticker"

def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    try:
        print("sending order")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False
    return order

def createFrame(msg):
    df = pd.DataFrame([msg])
    df = df.loc[:,['symbol','T','LP','CP']]
    df.columns = ['symbol', 'Time', 'LastPrice', 'ClosingPrice']
    df.LastPrice = df.LastPrice.astype(float)
    df.ClosingPrice = df.ClosingPrice.astype(float)
    df.Time = pd.to_datetime(df.Time, unit='ms')
    return df

def on_open(ws):
    print('open connection')


def on_close(ws):
    print('close connection')


def on_message(ws, message):
    global oneMinCounter, twoMinCounter

    print('received message')

    json_message = json.loads(message)


    startTime = time.time()

    try:
        

        for crypto in json_message:
            if allCrypto.get(crypto['s']) is None:
                allCrypto[crypto['s']] = {}
                allCrypto[crypto['s']]['CP'] = crypto['c']

            # symbol
            allCrypto[crypto['s']]['symbol'] = crypto['s']
            # Time
            allCrypto[crypto['s']]['T'] = crypto['E']
            # Last Price
            allCrypto[crypto['s']]['LP'] = crypto['c']

            if oneMinCounter == TIME_PERIOD:
                # Closing Price
                allCrypto[crypto['s']]['CP'] = crypto['c']
            
            if allCrypto[crypto['s']].get('CP') is not None:
                if (( float(allCrypto[crypto['s']]['LP']) / float(allCrypto[crypto['s']]['CP']) ) > PERCENT_INCREASE):
                    if pumpedCryptoDict.get(allCrypto[crypto['s']]['symbol']) is None:
                        # Sudden Price Increase Percentage
                        allCrypto[crypto['s']]['SPI'] =  float(allCrypto[crypto['s']]['LP']) / float(allCrypto[crypto['s']]['CP']) * 100.0
                        winsound.Beep(880, 300)
                        pumpedCryptoDict[allCrypto[crypto['s']]['symbol']] = allCrypto[crypto['s']]
                        pumpedCrypto.append(allCrypto[crypto['s']].copy())
                        frame = createFrame(allCrypto[crypto['s']])
                        frame.to_sql('PumpedCrypto', engine, if_exists='append', index=False)
            # if crypto['s'] == 'WNXMUSDT':
            #     print(crypto)

    except Exception as e:
        print(e)

    oneMinCounter += 1
    twoMinCounter += 1
    if oneMinCounter > TIME_PERIOD:
        oneMinCounter = 0
    # if twoMinCounter > 119:
    #     twoMinCounter = 0

    endTime = time.time()

    print("Last Price > Closing Price * {percentage}".format(percentage = PERCENT_INCREASE))
    for i in range(len(pumpedCrypto)):
        print(pumpedCrypto[i])
    print("Time past in seconds: {timeNow}".format(timeNow = twoMinCounter))


def run():
    try:
        start = False
        ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
        while(not start):
            time_now = datetime.now()
            time_now_seconds = time_now.second
            if(time_now_seconds == 0):
                start = True
        while True:
            ws.run_forever()
    except Exception as e:
        print(e)

run()

