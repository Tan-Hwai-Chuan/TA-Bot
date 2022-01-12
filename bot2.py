from enum import Flag
from logging import exception
import websocket, json, time
import sqlalchemy as sql
import pandas as pd
import config
import threading
import winsound
import math
from datetime import datetime
from binance.client import Client
from binance.enums import *
from tqdm import tqdm


TRADE_QUANTITY = 0.05

SOCKET ="wss://stream.binance.com:9443/ws/!ticker@arr"
ATR_PERCENT = 0.3
ONE_MIN_START = 0
ONE_MIN_END = 59
ADX_INDICATOR_PERIOD = 14
ADX_INDICATOR_WEIGHT = 1.0/ADX_INDICATOR_PERIOD
ADX_ARRAY_SIZE = 120
POS_DI_ARRAY_SIZE = 120
NEG_DI_ARRAY_SIZE = 120
CP_ARRAY_SIZE = 120
PHP_ARRAY_SIZE = 120
PLWP_ARRAY_SIZE = 120
DAY_CANDLES_PERIOD = "300 day ago UTC"
EMA_9 = 9
EMA_12 = 12
EMA_26 = 26
EMA_50 = 50
EMA_200 = 200
DATABASE_NAME = 'RECORD_CRYPTO'
PRINT_NAME = 'ADX_PEAK_TEST_3_ADX>15'
TRADING_FEES = 0.00075
BREAK_EVEN_RATIO = (1 + TRADING_FEES)/(1 - TRADING_FEES)
DESIRED_PROFIT_PERCENTAGE = BREAK_EVEN_RATIO + 0.001

client = Client(config.API_KEY, config.API_SECRET)

engine = sql.create_engine('sqlite:///PULLBACK_TEST.db')

cryptoEngine = sql.create_engine('sqlite:///AllCrypto.db')

cryptoKlineEngine = sql.create_engine('sqlite:///AllCryptoKline.db')

wallet = {}
boughtCrypto = {}
allCrypto = {}
dailyEMA = {}
cryptoArr = []
activeCrypto = []
pumpedCryptoDict = {}
pumpedCrypto = []
oneMinCounter = 0
twoMinCounter = 0
test = []
test1 = []
init = True

def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    try:
        print("sending order")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False
    return order

# Create frame for all coins database
def createFrame_general(msg):
    df = pd.DataFrame([msg])
    df = df.loc[:,['symbol','T','OP','LP','HP','LWP','CP','BID','ASK','NUM_QUOTE_TRADE',
                    'TR','POS_DM','NEG_DM','DX','PHP','PLWP','S_POS_DM','S_NEG_DM','ADX_ATR',
                    'ATR','POS_DI','NEG_DI','ADX']]
    df.columns = ['Symbol','Time','Open Price','Last Price','Curr High','Curr Low','Close Price',
                    'Best Bid','Best Ask','Number of Qoute Trades','True Range','Postive DM','Negative DM',
                    'DX','Previous High','Previous Low','Smoothed Positive DM','Smoothed Negative DM',
                    'ADX Average True Range','Acutal Average True Range','Positive DI','Negative DI',
                    'Average Directional Index']
    df.Time = pd.to_datetime(df.Time, unit='ms')
    # df.SellTime = pd.to_datetime(df.SellTime, unit='ms')
    return df

# Create frame for bought coin database
def createFrame_boughtCoin(msg):
    df = pd.DataFrame([msg])
    df = df.loc[:,['symbol','ATR','PULLBACK','stopLoss','boughtPrice','boughtAmt','boughtTime','boughtFees',
                    'sellPrice','sellAmt','sellTime','sellFees','Profit','Up/Down']]
    df.columns = ['symbol','ATR','PullBack','StopLoss','BoughtPrice', 'BoughtAmount','BoughtTime','BoughtFees',
                    'SellPrice','SellAmount','SellTime','SellFees','Profit','Up/Down']
    # df.BoughtTime = pd.to_datetime(df.BoughtTime, unit='ms')
    # df.SellTime = pd.to_datetime(df.SellTime, unit='ms')
    return df

def createCryptoFrame(msg):
    df = pd.DataFrame([msg])

# Calculate Directional Movement
def cal_dm(high, previous_high, low, previous_low):

    pos_dm = float(high) - float(previous_high)
    neg_dm = float(previous_low) - float(low)

    if pos_dm > neg_dm and pos_dm > 0:
        neg_dm = 0.0
    elif neg_dm > pos_dm and neg_dm > 0:
        pos_dm = 0.0
    else:
        pos_dm = 0.0
        neg_dm = 0.0

    return pos_dm, neg_dm

# Calculate True Range
def cal_tr(high, low, previous_close):
    true_range = max(
                    (float(high) - float(low)),
                    (float(high) - float(previous_close)),
                    (float(previous_close) - float(low))
                )
    return true_range

# Calculate Directional Index
def cal_di(s_dm, atr):
    if atr == 0.0:
        di = 0.0
    else:
        di = (s_dm/atr) * 100.0
    return di

# Calculate Directional Movement Index
def cal_dx(p_di, n_di):
    if(p_di + n_di) == 0:
        dx = 0
    else:
        dx =  ( abs(p_di - n_di) / (p_di + n_di) ) * 100.0
    return dx

def first_period_total(array):
    total = 0.0
    for indicator in array:
        total = total + indicator

    return total

def cal_ema(total_close, curr_close, curr_day, period, prev_ema):
    ema = 0.0
    if curr_day == period:
        ema = total_close/period
    elif curr_day > period:
        weight_ratio = 2 / (period + 1)
        ema = (curr_close * weight_ratio) + (prev_ema * (1 - weight_ratio))
    return ema

def find_pullback(closes, low_prices):
    close_len = len(closes)
    last_index = -1
    lowest_close = 0
    
    while -(last_index) < close_len:
        if(closes[last_index] > closes[last_index - 1]):
            last_index -= 1
        else:
            lowest_close = low_prices[last_index]
            return lowest_close
    return lowest_close

def find_peak_trough(closes, result_array):
    close_len  = len(closes)
    last_index = -1
    descending = True

    if(close_len < 2):
        return result_array

    if(closes[last_index] > closes[last_index - 1]):
        descending = True
    else:
        descending = False



    while -(last_index) < len(closes):
        if(descending):
            if(closes[last_index] <= closes[last_index - 1]):
                result_array.append({'H/L':'L','index':last_index})
                descending = False
            last_index -= 1
        elif(not descending):
            if(closes[last_index] >= closes[last_index - 1]):
                result_array.append({'H/L':'H','index':last_index})
                descending = True
            last_index -= 1
    return result_array

# def find_peak_trough(closes, result_array, index=-1):
#     close_len  = len(closes)
#     last_index = -1
#     index_tracker = index

#     if(close_len < 2):
#         return result_array

#     if(closes[last_index] > closes[last_index - 1]):
#         while -(last_index) < len(closes):
#             close_len -= 1
            
#             if(closes[last_index] <= closes[last_index - 1]):
#                 result_array.append({'H/L':'L','index':index_tracker})
#                 if close_len > 1:
#                     find_peak_trough(closes[0:close_len+1],result_array,index_tracker)
#                 return result_array
#             last_index -= 1
#             index_tracker -= 1
#     else:
#         while -(last_index) < len(closes):
#             close_len -= 1
            
#             if(closes[last_index] >= closes[last_index - 1]):
#                 result_array.append({'H/L':'H','index':index_tracker})
#                 if close_len > 1:
#                     find_peak_trough(closes[0:close_len+1],result_array,index_tracker)
#                 return result_array
#             last_index -= 1
#             index_tracker -= 1
#     return result_array

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

def on_open(ws):
    print('open connection')


def on_close(ws):
    print('close connection')


def init():
    allcryptotest = client.get_all_tickers()

    cryptotest = []


    for crypto in allcryptotest:
        if crypto['symbol'].endswith('USDT'):
            cryptotest.append(crypto['symbol'])
    try:
        for crypto in tqdm(cryptotest):
            kline = client.get_historical_klines(crypto, 
                                                    Client.KLINE_INTERVAL_1DAY,
                                                    DAY_CANDLES_PERIOD)
            total_close = 0.0
            kline_len = len(kline)
            init_len = len(kline)
            num_days = 0
            ma = 0.0
            ema_9 = 0.0
            ema_12 = 0.0
            ema_26 = 0.0
            ema_50 = 0.0
            ema_200 = 0.0
            dailyEMA[crypto] = {}

            while kline_len > 0:
                current_close = float(kline[-kline_len][4])
                total_close += current_close
                num_days += 1
                if(init_len < 9):
                    ma = cal_ema(total_close, current_close, num_days, init_len, ma)
                if(init_len >= 9):
                    ema_9 = cal_ema(total_close, current_close, num_days, EMA_9, ema_9)
                if(init_len >= 12):
                    ema_12 = cal_ema(total_close, current_close, num_days, EMA_12, ema_12)
                if(init_len >= 26):
                    ema_26 = cal_ema(total_close, current_close, num_days, EMA_26, ema_26)
                if(init_len >= 50):
                    ema_50 = cal_ema(total_close, current_close, num_days, EMA_50, ema_50)
                if(init_len >= 200):
                    ema_200 = cal_ema(total_close, current_close, num_days, EMA_200, ema_200)

                dailyEMA[crypto]['symbol'] = crypto
                dailyEMA[crypto]['MA'] = ma
                dailyEMA[crypto]['EMA_9'] = ema_9
                dailyEMA[crypto]['EMA_12'] = ema_12
                dailyEMA[crypto]['EMA_26'] = ema_26
                dailyEMA[crypto]['EMA_50'] = ema_50
                dailyEMA[crypto]['EMA_200'] = ema_200

                kline_len -= 1
    except Exception as e:
        print(e)



def on_message(ws, message):
    global oneMinCounter, twoMinCounter, init

    json_message = json.loads(message)

    startTime = time.time()


    if oneMinCounter > ONE_MIN_END:
        oneMinCounter = ONE_MIN_START
    try:
        for crypto in json_message:
            
            if crypto['s'].endswith('USDT'):
                # initiate crypto info
                if allCrypto.get(crypto['s']) is None:
                    # Save symbol in arr
                    cryptoArr.append(crypto['s'])
                    # use symbol as key
                    allCrypto[crypto['s']] = {}
                    # Symbol
                    allCrypto[crypto['s']]['symbol'] = crypto['s']
                    # Time
                    allCrypto[crypto['s']]['T'] = crypto['E']
                    # Open Price
                    allCrypto[crypto['s']]['OP'] = crypto['c']
                    # Last Price
                    allCrypto[crypto['s']]['LP'] = crypto['c']
                    # High Price
                    allCrypto[crypto['s']]['HP'] = crypto['c']
                    # Low Price
                    allCrypto[crypto['s']]['LWP'] = crypto['c']
                    # Closing Price
                    allCrypto[crypto['s']]['CP'] = [crypto['c']]
                    # Best Bid Price
                    allCrypto[crypto['s']]['BID'] = crypto['b']
                    # Best Ask Price
                    allCrypto[crypto['s']]['ASK'] = crypto['a']
                    # Total 24h rolling window number of trade
                    allCrypto[crypto['s']]['NUM_QUOTE_TRADE'] = crypto['q']
                    # Previous High Price
                    allCrypto[crypto['s']]['PHP'] = []
                    # Previous Low Price
                    allCrypto[crypto['s']]['PLWP'] = []
                    # 14 True Range
                    allCrypto[crypto['s']]['TR'] = []
                    # 14 Positive DM
                    allCrypto[crypto['s']]['POS_DM'] = []
                    # 14 Negative DM
                    allCrypto[crypto['s']]['NEG_DM'] = []
                    # Positive DI
                    allCrypto[crypto['s']]['POS_DI'] = []
                    # Negative DI
                    allCrypto[crypto['s']]['NEG_DI'] = []
                    # 14 DX
                    allCrypto[crypto['s']]['DX'] = []
                    # Average True Index
                    allCrypto[crypto['s']]['ADX'] = []
                    # Add active crypto
                    if float(allCrypto[crypto['s']]['NUM_QUOTE_TRADE']) > 10000000.0:
                        activeCrypto.append(crypto['s'])

                # Update Time
                allCrypto[crypto['s']]['T'] = crypto['E']
                # Update Last Price
                allCrypto[crypto['s']]['LP'] = crypto['c']
                # Update High Price
                allCrypto[crypto['s']]['HP'] = max( float(crypto['c']), float(allCrypto[crypto['s']]['HP']) )
                # Update Low Price
                allCrypto[crypto['s']]['LWP'] = min( float(crypto['c']), float(allCrypto[crypto['s']]['LWP']) )
                # Update Bid Price
                allCrypto[crypto['s']]['BID'] = crypto['b']
                # Update Ask Price
                allCrypto[crypto['s']]['ASK'] = crypto['a']
                # Update Number of Trade
                allCrypto[crypto['s']]['NUM_QUOTE_TRADE'] = crypto['q']

                ema = 1000000.0
                if(dailyEMA.get(crypto['s']) is not None):
                    if dailyEMA[crypto['s']]['EMA_50'] != 0:
                        ema = dailyEMA[crypto['s']]['EMA_200']
                    elif dailyEMA[crypto['s']]['EMA_50'] != 0:
                        ema = dailyEMA[crypto['s']]['EMA_50']
                    elif dailyEMA[crypto['s']]['EMA_26'] != 0:
                        ema = dailyEMA[crypto['s']]['EMA_26']
                    elif dailyEMA[crypto['s']]['EMA_12'] != 0:
                        ema = dailyEMA[crypto['s']]['EMA_12']
                    elif dailyEMA[crypto['s']]['EMA_9'] != 0:
                        ema = dailyEMA[crypto['s']]['EMA_9']
                    elif dailyEMA[crypto['s']]['MA'] != 0:
                        ema = dailyEMA[crypto['s']]['MA']

                #############################################################################################################
                # Making Trade Conditions

                if allCrypto[crypto['s']].get('ATR') is not None and allCrypto[crypto['s']]['ADX']:
                    
                    # Array for finding High and Lows
                    adxHL = []
                    # closesHL = []

                    adxHL = find_peak_trough(allCrypto[crypto['s']]['ADX'],adxHL)
                    # closesHL = find_peak_trough(allCrypto[crypto['s']]['CP'],closesHL)

                    if(len(adxHL) >= 2 and len(allCrypto[crypto['s']]['ADX']) > 4):
                        if ((( allCrypto[crypto['s']]['ATR'] / float(allCrypto[crypto['s']]['LP']) ) * 100.0) > ATR_PERCENT and
                                adxHL[0]['H/L'] == 'L' and
                                adxHL[1]['H/L'] == 'H' and
                                allCrypto[crypto['s']]['ADX'][adxHL[1]['index']] > 20 and
                                allCrypto[crypto['s']]['ADX'][-1] > allCrypto[crypto['s']]['ADX'][adxHL[1]['index']] and 
                                (allCrypto[crypto['s']]['ADX'][-2] < allCrypto[crypto['s']]['ADX'][adxHL[1]['index']] or
                                    allCrypto[crypto['s']]['ADX'][-3] < allCrypto[crypto['s']]['ADX'][adxHL[1]['index']] or
                                    allCrypto[crypto['s']]['ADX'][-4] < allCrypto[crypto['s']]['ADX'][adxHL[1]['index']]) and
                                # allCrypto[crypto['s']]['POS_DI'][adxHL[1]['index']] > allCrypto[crypto['s']]['NEG_DI'][adxHL[1]['index']] and
                                allCrypto[crypto['s']]['POS_DI'][-1] > allCrypto[crypto['s']]['NEG_DI'][-1] and
                                wallet['IN_POSITION'] == False and 
                                allCrypto[crypto['s']]['symbol'].endswith('USDT') and
                                float(allCrypto[crypto['s']]['NUM_QUOTE_TRADE']) > 10000000.0 and 
                                float(allCrypto[crypto['s']]['CP'][-1]) > ema
                                # and boughtCrypto.get(crypto['s']) is None
                            ):
                            
                            atr = allCrypto[crypto['s']]['ATR']
                            price = float(allCrypto[crypto['s']]['ASK'])
                            last_pullback = find_pullback(allCrypto[crypto['s']]['CP'],allCrypto[crypto['s']]['PLWP'])
                            pullback = True
                            if (last_pullback and
                                (((float(allCrypto[crypto['s']]['ASK']) - last_pullback) / float(allCrypto[crypto['s']]['ASK'])) * 100) > ATR_PERCENT*2):
                                amount = (wallet['Capital'] * 0.005) / ((float(allCrypto[crypto['s']]['ASK']) - last_pullback))
                                fees = amount*price*0.00075
                                pullback = True
                            else:
                                amount = (wallet['Capital'] * 0.005) / (atr * 2)
                                fees = amount*price*0.00075
                                pullback = False

                            buy_crypto(wallet=wallet, amount=amount, price=price, fees=fees)

                            boughtCrypto[crypto['s']] = {}
                            boughtCrypto[crypto['s']]['symbol'] = crypto['s']
                            boughtCrypto[crypto['s']]['ATR'] = atr
                            boughtCrypto[crypto['s']]['PULLBACK'] = last_pullback
                            if pullback == True:
                                boughtCrypto[crypto['s']]['stopLoss'] = "PullBack"
                            else:
                                boughtCrypto[crypto['s']]['stopLoss'] = "ATR"
                            boughtCrypto[crypto['s']]['boughtPrice'] = price
                            boughtCrypto[crypto['s']]['boughtAmt'] = amount
                            boughtCrypto[crypto['s']]['boughtTime'] = datetime.now()
                            boughtCrypto[crypto['s']]['boughtFees'] = fees

                            wallet['IN_POSITION'] = True
                            wallet['COIN'] = crypto['s']
                            wallet['ASSET_WORTH'] = price * amount
                            wallet['total_trade'] += 1
                            print(wallet)

                        elif(wallet['IN_POSITION'] == True and allCrypto[crypto['s']]['symbol'] == wallet['COIN']):

                            current_bid_price = float(allCrypto[crypto['s']]['BID'])
                            amount = boughtCrypto[crypto['s']]['boughtAmt']
                            fees = (current_bid_price * amount) * 0.00075

                            if (boughtCrypto[crypto['s']]['stopLoss'] == "PullBack"):

                                if(current_bid_price > boughtCrypto[crypto['s']]['boughtPrice'] + 
                                    ((boughtCrypto[crypto['s']]['boughtPrice'] - boughtCrypto[crypto['s']]['PULLBACK']) * 1.5) or
                                    current_bid_price < boughtCrypto[crypto['s']]['PULLBACK']):
                                    sell_crypto(wallet=wallet, amount=amount, price=current_bid_price, fees=fees)

                                    boughtCrypto[crypto['s']]['sellPrice'] = current_bid_price
                                    boughtCrypto[crypto['s']]['sellAmt'] = amount
                                    boughtCrypto[crypto['s']]['sellTime'] = datetime.now()
                                    boughtCrypto[crypto['s']]['sellFees'] = fees
                                    boughtCrypto[crypto['s']]['Profit'] = ((boughtCrypto[crypto['s']]['sellPrice'] * boughtCrypto[crypto['s']]['sellAmt']) -
                                                                            (boughtCrypto[crypto['s']]['boughtPrice'] * boughtCrypto[crypto['s']]['boughtAmt']) -
                                                                            (boughtCrypto[crypto['s']]['boughtFees'] + boughtCrypto[crypto['s']]['sellFees']))
                                    if(current_bid_price > boughtCrypto[crypto['s']]['boughtPrice'] + 
                                    ((boughtCrypto[crypto['s']]['boughtPrice'] - boughtCrypto[crypto['s']]['PULLBACK']) * 1.5)):                                                
                                        boughtCrypto[crypto['s']]['Up/Down'] = "UP"
                                    else:
                                        boughtCrypto[crypto['s']]['Up/Down'] = "DOWN"
                                    wallet['IN_POSITION'] = False
                                    wallet['COIN'] = ""
                                    wallet['ASSET_WORTH'] = 0.0
                                    if(current_bid_price > boughtCrypto[crypto['s']]['boughtPrice'] + 
                                    ((boughtCrypto[crypto['s']]['boughtPrice'] - boughtCrypto[crypto['s']]['PULLBACK']) * 1.5)):                                                
                                        wallet['win_trade'] += 1
                                    else:
                                        wallet['lose_trade'] += 1
                                    

                                    frame = createFrame_boughtCoin(boughtCrypto[crypto['s']])
                                    frame.to_sql(DATABASE_NAME, engine, if_exists='append', index=False)
                                    print(wallet)
                            else:
                                if(current_bid_price > (boughtCrypto[crypto['s']]['boughtPrice'] + (boughtCrypto[crypto['s']]['ATR'] * 3)) or
                                    current_bid_price < (boughtCrypto[crypto['s']]['boughtPrice'] - (boughtCrypto[crypto['s']]['ATR'] * 2))):

                                    sell_crypto(wallet=wallet, amount=amount, price=current_bid_price, fees=fees)

                                    boughtCrypto[crypto['s']]['sellPrice'] = current_bid_price
                                    boughtCrypto[crypto['s']]['sellAmt'] = amount
                                    boughtCrypto[crypto['s']]['sellTime'] = datetime.now()
                                    boughtCrypto[crypto['s']]['sellFees'] = fees
                                    boughtCrypto[crypto['s']]['Profit'] = ((boughtCrypto[crypto['s']]['sellPrice'] * boughtCrypto[crypto['s']]['sellAmt']) -
                                                                            (boughtCrypto[crypto['s']]['boughtPrice'] * boughtCrypto[crypto['s']]['boughtAmt']) -
                                                                            (boughtCrypto[crypto['s']]['boughtFees'] + boughtCrypto[crypto['s']]['sellFees']))
                                    if(current_bid_price > (boughtCrypto[crypto['s']]['boughtPrice'] + (boughtCrypto[crypto['s']]['ATR'] * 3))):
                                        boughtCrypto[crypto['s']]['Up/Down'] = "UP"
                                    else:
                                        boughtCrypto[crypto['s']]['Up/Down'] = "DOWN"
                                    wallet['IN_POSITION'] = False
                                    wallet['COIN'] = ""
                                    wallet['ASSET_WORTH'] = 0.0
                                    if(current_bid_price > (boughtCrypto[crypto['s']]['boughtPrice'] + (boughtCrypto[crypto['s']]['ATR'] * 3))):
                                        wallet['win_trade'] += 1
                                    else:
                                        wallet['lose_trade'] += 1
                                    

                                    frame = createFrame_boughtCoin(boughtCrypto[crypto['s']])
                                    frame.to_sql(DATABASE_NAME, engine, if_exists='append', index=False)
                                    print(wallet)
            
                        ############################################################################################################################

        if oneMinCounter == ONE_MIN_START:
            for crypto in cryptoArr:
                # Update Open Price
                allCrypto[crypto]['OP'] = allCrypto[crypto]['LP']
                # Reset High Price
                allCrypto[crypto]['HP'] = allCrypto[crypto]['LP']
                # Reset Low Price
                allCrypto[crypto]['LWP'] = allCrypto[crypto]['LP']

        elif oneMinCounter == ONE_MIN_END:
            for crypto in cryptoArr:
                if (allCrypto[crypto]['PHP'] and
                    allCrypto[crypto]['PLWP']):

                    #############################################################################
                    #  Calculate ADX

                    if ((len(allCrypto[crypto]['POS_DM']) < ADX_INDICATOR_PERIOD) and
                        (len(allCrypto[crypto]['NEG_DM']) < ADX_INDICATOR_PERIOD)):
                        # Calculate positive and negative DM
                        pos_dm, neg_dm = cal_dm(allCrypto[crypto]['HP'], allCrypto[crypto]['PHP'][-1], allCrypto[crypto]['LWP'], allCrypto[crypto]['PLWP'][-1])

                        # Update positive and negative DM
                        allCrypto[crypto]['POS_DM'].append(pos_dm)
                        allCrypto[crypto]['NEG_DM'].append(neg_dm)

                        # Calculate Smoothed DM
                        if ((len(allCrypto[crypto]['POS_DM']) == ADX_INDICATOR_PERIOD) and
                            (len(allCrypto[crypto]['NEG_DM']) == ADX_INDICATOR_PERIOD)):
                            total_pos_dm = first_period_total(allCrypto[crypto]['POS_DM'])
                            total_neg_dm = first_period_total(allCrypto[crypto]['NEG_DM'])

                            # init smooted DM
                            allCrypto[crypto]['S_POS_DM'] = total_pos_dm
                            allCrypto[crypto]['S_NEG_DM'] = total_neg_dm

                    else:
                        # Only keep the most recent DMs
                        pos_dm, neg_dm = cal_dm(allCrypto[crypto]['HP'], allCrypto[crypto]['PHP'][-1], allCrypto[crypto]['LWP'],allCrypto[crypto]['PLWP'][-1])

                        # Update positive and negative DM
                        allCrypto[crypto]['POS_DM'].pop(0)
                        allCrypto[crypto]['POS_DM'].append(pos_dm)
                        allCrypto[crypto]['NEG_DM'].pop(0)
                        allCrypto[crypto]['NEG_DM'].append(neg_dm)

                        # Update DM with Wilder's smoothing technique
                        allCrypto[crypto]['S_POS_DM'] = (allCrypto[crypto]['S_POS_DM'] - (allCrypto[crypto]['S_POS_DM']/ADX_INDICATOR_PERIOD)
                                                            + pos_dm)
                        allCrypto[crypto]['S_NEG_DM'] = (allCrypto[crypto]['S_NEG_DM'] - (allCrypto[crypto]['S_NEG_DM']/ADX_INDICATOR_PERIOD)
                                                            + neg_dm)

                    if len(allCrypto[crypto]['TR']) < ADX_INDICATOR_PERIOD:
                        # Calculate True Range
                        true_range = cal_tr(allCrypto[crypto]['HP'], allCrypto[crypto]['LWP'], allCrypto[crypto]['CP'][-1])

                        # Update True Range
                        allCrypto[crypto]['TR'].append(true_range)

                        if len(allCrypto[crypto]['TR']) == ADX_INDICATOR_PERIOD:
                            total_tr = first_period_total(allCrypto[crypto]['TR'])

                            # init Average True Range
                            allCrypto[crypto]['ADX_ATR'] = total_tr
                            allCrypto[crypto]['ATR'] = total_tr/ADX_INDICATOR_PERIOD

                    else:
                        # Only Keep the most recent 14 TR
                        true_range = cal_tr(allCrypto[crypto]['HP'], allCrypto[crypto]['LWP'], allCrypto[crypto]['CP'][-1])

                        # Remove first TR and add recent TR
                        first_tr = allCrypto[crypto]['TR'].pop(0)
                        allCrypto[crypto]['TR'].append(true_range)

                        # Update ATR with Wilder's Smoothing Method for ADX
                        allCrypto[crypto]['ADX_ATR'] = allCrypto[crypto]['ADX_ATR'] - (allCrypto[crypto]['ADX_ATR']/ADX_INDICATOR_PERIOD) + true_range

                        # Update ATR by finding the average
                        allCrypto[crypto]['ATR'] = ((allCrypto[crypto]['ATR'] * ADX_INDICATOR_PERIOD) - first_tr + true_range )/ ADX_INDICATOR_PERIOD

                # Calculate +/-DI and DX
                if(allCrypto[crypto].get('S_POS_DM') is not None and
                    allCrypto[crypto].get('S_POS_DM') is not None and
                    allCrypto[crypto].get('ADX_ATR') is not None):

                    # Calculate DI Value
                    pos_di = cal_di(allCrypto[crypto]['S_POS_DM'], allCrypto[crypto]['ADX_ATR'])
                    neg_di = cal_di(allCrypto[crypto]['S_NEG_DM'], allCrypto[crypto]['ADX_ATR'])

                    if(len(allCrypto[crypto]['POS_DI']) < POS_DI_ARRAY_SIZE):
                        # Save DI values
                        allCrypto[crypto]['POS_DI'].append(pos_di)
                    else:
                        allCrypto[crypto]['POS_DI'].pop(0)
                        allCrypto[crypto]['POS_DI'].append(pos_di)

                    if(len(allCrypto[crypto]['NEG_DI']) < NEG_DI_ARRAY_SIZE):
                        allCrypto[crypto]['NEG_DI'].append(neg_di)
                    else:
                        allCrypto[crypto]['NEG_DI'].pop(0)
                        allCrypto[crypto]['NEG_DI'].append(neg_di)

                    # DX
                    if (len(allCrypto[crypto]['DX']) < ADX_INDICATOR_PERIOD):

                        # Calculate DX value
                        dx = cal_dx(pos_di, neg_di)

                        # Update DX
                        allCrypto[crypto]['DX'].append(dx)

                        if (len(allCrypto[crypto]['DX']) == ADX_INDICATOR_PERIOD):
                            # Calculate simple average DX
                            total_dx = first_period_total(allCrypto[crypto]['DX'])

                            allCrypto[crypto]['ADX'].append(total_dx/ADX_INDICATOR_PERIOD)
                    else:
                        # Only Keep the most recent 14 DX
                        dx = cal_dx(pos_di, neg_di)

                        # Remove first DX and add recent DX
                        allCrypto[crypto]['DX'].pop(0)
                        allCrypto[crypto]['DX'].append(dx)

                        adx = ((allCrypto[crypto]['ADX'][-1] * (ADX_INDICATOR_PERIOD - 1)) + dx)/ADX_INDICATOR_PERIOD
                        if (len(allCrypto[crypto]['ADX']) < ADX_ARRAY_SIZE):
                            # Update ADX with Wilder's Second Smoothing Method
                            allCrypto[crypto]['ADX'].append(adx)
                        else:
                            allCrypto[crypto]['ADX'].pop(0)
                            allCrypto[crypto]['ADX'].append(adx)


                # ADX Calculation end
                ##############################################################################################
                if(len(allCrypto[crypto]['CP']) < CP_ARRAY_SIZE):
                    # Update Closing Price
                    allCrypto[crypto]['CP'].append(allCrypto[crypto]['LP'])
                else:
                    allCrypto[crypto]['CP'].pop(0)
                    allCrypto[crypto]['CP'].append(allCrypto[crypto]['LP'])
                if(len(allCrypto[crypto]['PHP']) < PHP_ARRAY_SIZE):
                    # Update Previous High Price
                    allCrypto[crypto]['PHP'].append(allCrypto[crypto]['HP'])
                else:
                    allCrypto[crypto]['PHP'].pop(0)
                    allCrypto[crypto]['PHP'].append(allCrypto[crypto]['HP'])
                if(len(allCrypto[crypto]['PLWP']) < PLWP_ARRAY_SIZE):
                    # Update Precious Low Price
                    allCrypto[crypto]['PLWP'].append(allCrypto[crypto]['LWP'])
                else:
                    allCrypto[crypto]['PLWP'].pop(0)
                    allCrypto[crypto]['PLWP'].append(allCrypto[crypto]['HP'])

                
            for crypto in activeCrypto:
                if allCrypto[crypto]['ADX']:
                    cryptoSymbol = crypto
                    cryptoDB = {}
                    cryptoDB[crypto] = {}
                    cryptoDB[crypto]['symbol'] = allCrypto[crypto]['symbol']
                    cryptoDB[crypto]['T'] = allCrypto[crypto]['T']
                    cryptoDB[crypto]['OP'] = allCrypto[crypto]['OP']
                    cryptoDB[crypto]['LP'] = allCrypto[crypto]['LP']
                    cryptoDB[crypto]['HP'] = allCrypto[crypto]['HP']
                    cryptoDB[crypto]['LWP'] = allCrypto[crypto]['LWP']
                    cryptoDB[crypto]['CP'] = allCrypto[crypto]['CP'][-1]
                    cryptoDB[crypto]['BID'] = allCrypto[crypto]['BID']
                    cryptoDB[crypto]['ASK'] = allCrypto[crypto]['ASK']
                    cryptoDB[crypto]['NUM_QUOTE_TRADE'] = allCrypto[crypto]['NUM_QUOTE_TRADE']
                    cryptoDB[crypto]['TR'] = allCrypto[crypto]['TR'][-1]
                    cryptoDB[crypto]['POS_DM'] = allCrypto[crypto]['POS_DM'][-1]
                    cryptoDB[crypto]['NEG_DM'] = allCrypto[crypto]['NEG_DM'][-1]
                    cryptoDB[crypto]['DX'] = allCrypto[crypto]['DX'][-1]
                    cryptoDB[crypto]['PHP'] = allCrypto[crypto]['PHP'][-1]
                    cryptoDB[crypto]['PLWP'] = allCrypto[crypto]['PLWP'][-1]
                    cryptoDB[crypto]['S_POS_DM'] = allCrypto[crypto]['S_POS_DM']
                    cryptoDB[crypto]['S_NEG_DM'] = allCrypto[crypto]['S_NEG_DM']
                    cryptoDB[crypto]['ADX_ATR'] = allCrypto[crypto]['ADX_ATR']
                    cryptoDB[crypto]['ATR'] = allCrypto[crypto]['ATR']
                    cryptoDB[crypto]['POS_DI'] = allCrypto[crypto]['POS_DI'][-1]
                    cryptoDB[crypto]['NEG_DI'] = allCrypto[crypto]['NEG_DI'][-1]
                    cryptoDB[crypto]['ADX'] = allCrypto[crypto]['ADX'][-1]
                    frame = createFrame_general(cryptoDB[crypto])
                    frame.to_sql(cryptoSymbol, cryptoEngine, if_exists='append', index=False)

    except Exception as e:
        winsound.Beep(880, 300)
        print(e)

    twoMinCounter += 1
    oneMinCounter += 1

    endTime = time.time()
    # print(endTime - startTime)
    # print(oneMinCounter)
    # print(boughtCrypto)
    # print(PRINT_NAME)
    # print(wallet)
    # ws.close()
        

def run():
    try:
        start = False
        init_wallet(wallet)
        ts = time.time()
        te = time.time()
        print(te - ts)
        ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
        init()  
        while True:
            while(not start):
                time_now = datetime.now()
                time_now_seconds = time_now.second
                if(time_now_seconds == 0):
                    start = True
            ws.run_forever()
        # ws.run_forever()
    except Exception as e:
        print(e)


run()

