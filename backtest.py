from enum import Flag
from logging import exception
import websocket, json, time
import sqlalchemy as sql
import pandas as pd
import config
import winsound
from datetime import datetime
from binance.client import Client
from binance.enums import *
from tqdm import tqdm

client = Client(config.API_KEY, config.API_SECRET)

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
DAY_CANDLES_PERIOD = "200 days ago UTC"
EMA_9 = 9
EMA_12 = 12
EMA_26 = 26
EMA_50 = 50
EMA_200 = 200
DATABASE_NAME = 'RECORD_CRYPTO'
PRINT_NAME = 'ADX_PEAK_TEST_3_ADX>15'
TRADING_FEES = 0.00075
TRADE_QUANTITY = 0.05
BREAK_EVEN_RATIO = (1 + TRADING_FEES)/(1 - TRADING_FEES)
DESIRED_PROFIT_PERCENTAGE = BREAK_EVEN_RATIO + 0.001
ACTIVE_CRYPTO_TRADING_VOLUME = 10000000

dailyEMA = {}

def cal_ema(total_close, curr_close, curr_day, period, prev_ema):
    ema = 0.0
    if curr_day == period:
        ema = total_close/period
    elif curr_day > period:
        weight_ratio = 2 / (period + 1)
        ema = (curr_close * weight_ratio) + (prev_ema * (1 - weight_ratio))
    return ema

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

def init():
    allcryptotest = client.get_ticker()

    cryptotest = []


    for crypto in allcryptotest:
        if crypto['symbol'].endswith('USDT') and float(crypto['quoteVolume']) > ACTIVE_CRYPTO_TRADING_VOLUME:
            cryptotest.append(crypto['symbol'])
    try:
        for crypto in tqdm(cryptotest):
            kline = client.get_historical_klines(crypto, 
                                                    Client.KLINE_INTERVAL_1MINUTE,
                                                    DAY_CANDLES_PERIOD)
            print(kline)
            total_close = 0.0
            kline_len = len(kline)
            init_len = len(kline)
            num_days = 0
            ema = 0.0
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
                dailyEMA[crypto]['EMA'] = 0.0

                if ema_200 != 0:
                    dailyEMA[crypto]['EMA'] = ema_200
                elif ema_50 != 0:
                    dailyEMA[crypto]['EMA'] = ema_50
                elif ema_26 != 0:
                    dailyEMA[crypto]['EMA'] = ema_26
                elif ema_12 != 0:
                    dailyEMA[crypto]['EMA'] = ema_12
                elif ema_9 != 0:
                    dailyEMA[crypto]['EMA'] = ema_9
                elif ma != 0:
                    dailyEMA[crypto]['EMA'] = ma

                kline_len -= 1
    except Exception as e:
        print(e)


start = datetime.now()
init()
end = datetime.now()
print(end - start)