from csv import excel_tab
from enum import Flag
from logging import exception
from pickle import HIGHEST_PROTOCOL
import websocket, json, time
import sqlalchemy as sql
import pandas as pd
import config
import winsound
import ta_cal
import virtual_wallet
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
ADX_ARRAY_SIZE = 120
POS_DI_ARRAY_SIZE = 120
NEG_DI_ARRAY_SIZE = 120
CP_ARRAY_SIZE = 120
HP_ARRAY_SIZE = 120
LWP_ARRAY_SIZE = 120
MACD_ARRAY_SIZE = 120
DAY_CANDLES_PERIOD = "1000 days ago UTC"
MINUTE_CANDLES_PERIOD = "4 year ago UTC"
MINUTE_KLINE_INTERVAL = Client.KLINE_INTERVAL_5MINUTE
EMA_9 = 9
EMA_12 = 12
EMA_26 = 26
EMA_50 = 50
EMA_200 = 200
KLINE_OPEN_INDEX = 1
KLINE_HIGH_INDEX = 2
KLINE_LOW_INDEX = 3
KLINE_CLOSE_INDEX = 4
KLINE_VOLUME_INDEX = 5
DATABASE_NAME = 'RECORD_CRYPTO'
PRINT_NAME = 'ADX_PEAK_TEST_3_ADX>15'
TRADING_FEES = 0.00075
TRADE_QUANTITY = 0.05
BREAK_EVEN_RATIO = (1 + TRADING_FEES)/(1 - TRADING_FEES)
DESIRED_PROFIT_PERCENTAGE = BREAK_EVEN_RATIO + 0.001
ACTIVE_CRYPTO_TRADING_VOLUME = 10000000

dailyEMA = {}
wallet = {}
boughtCrypto = {}

def init():

    try:
        allcryptotest = client.get_ticker()

        cryptotest = []

        for crypto in allcryptotest:
            if crypto['symbol'].endswith('USDT') and float(crypto['quoteVolume']) > ACTIVE_CRYPTO_TRADING_VOLUME:
                cryptotest.append(crypto['symbol'])
    except Exception as e:
        print("Error adding active crypto")
        print(e)

    try:
        for crypto in tqdm(cryptotest):
            klines = client.get_historical_klines(crypto, 
                                                    Client.KLINE_INTERVAL_1DAY,
                                                    DAY_CANDLES_PERIOD)
            total_close = 0.0
            kline_len = len(klines)
            init_len = len(klines)
            num_days = 0
            ma = 0.0
            ema_9 = 0.0
            ema_12 = 0.0
            ema_26 = 0.0
            ema_50 = 0.0
            ema_200 = 0.0
            dailyEMA[crypto] = {}

            while kline_len > 0:
                current_close = float(klines[-kline_len][KLINE_CLOSE_INDEX])
                total_close += current_close
                num_days += 1
                if(init_len < 9):
                    ma = ta_cal.cal_ema(total_close, current_close, num_days, init_len, ma)
                if(init_len > 9):
                    ema_9 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_9, ema_9)
                if(init_len > 12):
                    ema_12 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_12, ema_12)
                if(init_len > 26):
                    ema_26 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_26, ema_26)
                if(init_len > 50):
                    ema_50 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_50, ema_50)
                if(init_len > 200):
                    ema_200 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_200, ema_200)

                dailyEMA[crypto]['symbol'] = crypto
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
        print("Error Calculating EMA")
        print(e)
    
    try:
        short_listed_crypto = []

        for crypto in allcryptotest:
            if dailyEMA.get(crypto['symbol']) is not None:
                if crypto['symbol'].endswith('USDT') and float(crypto['lastPrice']) > dailyEMA[crypto['symbol']]['EMA']:
                    short_listed_crypto.append(crypto['symbol'])
        return short_listed_crypto
    
    except Exception as e:
        print("Error adding short listed crypto")
        print(e)


def adx_bot(short_listed_crypto):
    try:
        for crypto in tqdm(short_listed_crypto):
            klines = client.get_historical_klines(crypto, 
                                                        MINUTE_KLINE_INTERVAL,
                                                        MINUTE_CANDLES_PERIOD)
            kline_len = len(klines)

            # Init smoothed DM values
            pos_dms = []
            neg_dms = []
            s_pos_dm = 0.0
            s_neg_dm = 0.0

            # Init Average True Range values
            tr = []
            adx_atr = 0.0
            atr = 0.0

            # Init DI values
            pos_dis = []
            neg_dis = []

            # Init ADX values
            dxs = []
            adx = 0.0
            adxs = []

            # Init closing prices for buying conditions
            closes = []
            highs = []
            lows = []

            # Init values to find EMA
            total_close = 0.0
            num_days = 0
            ema = 0.0
            ma = 0.0
            ema_9 = 0.0
            ema_12 = 0.0
            ema_26 = 0.0
            ema_50 = 0.0
            ema_200 = 0.0

            # Init values for MACD
            macd = 0.0
            signal = 0.0
            total_macd = 0.0
            num_sig = 0
            macds = []
            macd_sigs = []


            for i in range(kline_len):

                current_close = float(klines[i][KLINE_CLOSE_INDEX])
                total_close += current_close
                num_days += 1
                if(kline_len < 9):
                    ma = ta_cal.cal_ema(total_close, current_close, num_days, kline_len, ma)
                if(kline_len > 9):
                    ema_9 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_9, ema_9)
                if(kline_len > 12):
                    ema_12 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_12, ema_12)
                if(kline_len > 26):
                    ema_26 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_26, ema_26)
                if(kline_len > 50):
                    ema_50 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_50, ema_50)
                if(kline_len > 200):
                    ema_200 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_200, ema_200)
                
                if ema_200 != 0:
                    ema = ema_200
                elif ema_50 != 0:
                    ema = ema_50
                elif ema_26 != 0:
                    ema = ema_26
                elif ema_12 != 0:
                    ema = ema_12
                elif ema_9 != 0:
                    ema = ema_9
                elif ma != 0:
                    ema = ma

                # Initiate OHLC values
                open = float(klines[i][KLINE_OPEN_INDEX])
                high = float(klines[i][KLINE_HIGH_INDEX])
                low = float(klines[i][KLINE_LOW_INDEX])
                close = float(klines[i][KLINE_CLOSE_INDEX])

                if i == 0:
                    prev_open = 0.0
                    prev_high = 0.0
                    prev_low = 0.0
                    prev_close = 0.0
                else:
                    prev_open = float(klines[i-1][KLINE_OPEN_INDEX])
                    prev_high = float(klines[i-1][KLINE_HIGH_INDEX])
                    prev_low = float(klines[i-1][KLINE_LOW_INDEX])
                    prev_close = float(klines[i-1][KLINE_CLOSE_INDEX])

                    #########################################################################################################
                    # Calculate MACD

                    if i >= EMA_26 - 1:
                        macd = ta_cal.cal_macd(ema_12, ema_26)
                        ta_cal.insert_till_max(macds, macd, MACD_ARRAY_SIZE)
                        total_macd += macd
                        num_sig += 1
                    if len(macds) >= EMA_9:
                        signal = ta_cal.cal_ema(total_macd, macd, num_sig, EMA_9, signal)
                        ta_cal.insert_till_max(macd_sigs, signal, MACD_ARRAY_SIZE)


                    #########################################################################################################
                    # Calculate DM
                    pos_dm , neg_dm = ta_cal.cal_dm(high, prev_high, low, prev_low)

                    ta_cal.insert_till_max(pos_dms, pos_dm, ADX_INDICATOR_PERIOD)
                    ta_cal.insert_till_max(neg_dms, neg_dm, ADX_INDICATOR_PERIOD)

                    if len(pos_dms) == ADX_INDICATOR_PERIOD:
                        if s_pos_dm == 0.0:
                            s_pos_dm = ta_cal.first_period_total(pos_dms)
                        else:
                            s_pos_dm = ta_cal.wilder_first_smoothing(pos_dm, s_pos_dm, ADX_INDICATOR_PERIOD)
                    if len(neg_dms) == ADX_INDICATOR_PERIOD:
                        if s_neg_dm == 0.0:
                            s_neg_dm = ta_cal.first_period_total(neg_dms)
                        else:
                            s_neg_dm = ta_cal.wilder_first_smoothing(neg_dm, s_neg_dm, ADX_INDICATOR_PERIOD)
                    ###########################################################################################################

                    ###########################################################################################################
                    # Calculate ATR
                    true_range = ta_cal.cal_tr(high, low, prev_close)

                    previous_first_tr = ta_cal.insert_till_max(tr, true_range, ADX_INDICATOR_PERIOD, return_first_value=True)

                    if len(tr) == ADX_INDICATOR_PERIOD:
                        if adx_atr == 0.0:
                            adx_atr = ta_cal.first_period_total(tr)
                        else:
                            adx_atr = ta_cal.wilder_first_smoothing(true_range, adx_atr, ADX_INDICATOR_PERIOD)
                        if atr == 0.0:
                            atr = ta_cal.first_period_total(tr)/14
                        else:
                            atr = ((atr * ADX_INDICATOR_PERIOD) - previous_first_tr + true_range) / ADX_INDICATOR_PERIOD
                    ###########################################################################################################

                    ###########################################################################################################
                    # Calculate DI
                    if adx_atr != 0.0 and s_neg_dm != 0.0 and s_pos_dm != 0.0:
                        pos_di = ta_cal.cal_di(s_pos_dm, adx_atr)
                        neg_di = ta_cal.cal_di(s_neg_dm, adx_atr)

                        ta_cal.insert_till_max(pos_dis, pos_di, POS_DI_ARRAY_SIZE)
                        ta_cal.insert_till_max(neg_dis, neg_di, NEG_DI_ARRAY_SIZE)
                    ###########################################################################################################

                    ###########################################################################################################
                    # Calculate DX (Repeat if statement for readability)
                    if adx_atr != 0.0 and s_neg_dm != 0.0 and s_pos_dm != 0.0:
                        dx = ta_cal.cal_dx(pos_di, neg_di)

                        ta_cal.insert_till_max(dxs, dx, ADX_INDICATOR_PERIOD)

                        if len(dxs) == ADX_INDICATOR_PERIOD:
                            if adx == 0.0:
                                adx = ta_cal.first_period_total(dxs)
                            else:
                                adx = ta_cal.wilder_second_smoothing(dx, adx, ADX_INDICATOR_PERIOD)

                            ta_cal.insert_till_max(adxs, adx, ADX_ARRAY_SIZE)
                            ta_cal.insert_till_max(closes, close, CP_ARRAY_SIZE)
                            ta_cal.insert_till_max(highs, high, HP_ARRAY_SIZE)
                            ta_cal.insert_till_max(lows, low, LWP_ARRAY_SIZE)

                    ############################################################################################################
                    
                    ############################################################################################################
                    # Buying conditions
                    if len(adxs) != 0:
                        adxHL = []

                        adxHL = ta_cal.find_peak_trough(adxs, adxHL)

                        if len(adxHL) > 2 and len(adxs) > 4 and len(macd_sigs) > 0:
                            if (((atr / open ) * 100.0) > ATR_PERCENT and
                                adxHL[0]['H/L'] == 'L' and
                                adxHL[1]['H/L'] == 'H' and
                                adxs[adxHL[1]['index']] > 20 and
                                adxs[-1] > adxs[adxHL[1]['index']] and 
                                adxs[-2] < adxs[adxHL[1]['index']] and
                                pos_dis[adxHL[1]['index']] > neg_dis[adxHL[1]['index']] and
                                pos_dis[-1] > neg_dis[-1] and
                                # macds[-1] < 0 and
                                macds[-1] > macd_sigs[-1] and
                                ema != 0.0 and
                                open > ema and
                                ema_9 > ema_50 and
                                ema_50 > ema_200 and
                                wallet['IN_POSITION'] == False
                                ):
                                price = open
                                last_pullback = ta_cal.find_pullback(closes, lows)
                                pullback = True
                                if (last_pullback and 
                                    (((price - last_pullback) / price) * 100) > ATR_PERCENT*2):
                                    amount = (wallet['Capital'] * 0.005) / (price - last_pullback)
                                    fees = amount*price*0.00075
                                    pullback = True
                                else:
                                    amount = (wallet['Capital'] * 0.005) / (atr * 2)
                                    fees = amount*price*0.00075
                                    pullback = False
                                virtual_wallet.buy_crypto(wallet, amount, price, fees)

                                boughtCrypto['symbol'] = crypto
                                boughtCrypto['ATR'] = atr
                                boughtCrypto['PULLBACK'] = last_pullback
                                if pullback == True:
                                    boughtCrypto['stopLoss'] = "PullBack"
                                else:
                                    boughtCrypto['stopLoss'] = "ATR"
                                boughtCrypto['boughtPrice'] = price
                                boughtCrypto['boughtAmt'] = amount
                                boughtCrypto['boughtTime'] = datetime.now()
                                boughtCrypto['boughtFees'] = fees

                                wallet['IN_POSITION'] = True
                                wallet['COIN'] = crypto
                                wallet['ASSET_WORTH'] = price * amount
                                wallet['total_trade'] += 1
                            elif wallet['IN_POSITION'] == True:
                                sell_price = 0.0
                                if (boughtCrypto['stopLoss'] == "PullBack"):
                                    if(high > boughtCrypto['boughtPrice'] + 
                                        ((boughtCrypto['boughtPrice'] - 
                                        boughtCrypto['PULLBACK']) * 2)):
                                        sell_price =    (boughtCrypto['boughtPrice'] + 
                                                            ((boughtCrypto['boughtPrice'] - 
                                                            boughtCrypto['PULLBACK']) * 2))
                                    elif(low < boughtCrypto['PULLBACK']):
                                        sell_price = boughtCrypto['PULLBACK']

                                    amount = boughtCrypto['boughtAmt']
                                    fees = (sell_price * amount) * 0.00075

                                    if sell_price != 0.0:
                                        virtual_wallet.sell_crypto(wallet, amount, sell_price, fees)

                                        boughtCrypto['sellPrice'] = sell_price
                                        boughtCrypto['sellAmt'] = amount
                                        boughtCrypto['sellTime'] = datetime.now()
                                        boughtCrypto['sellFees'] = fees
                                        boughtCrypto['Profit'] = ((boughtCrypto['sellPrice'] * boughtCrypto['sellAmt']) -
                                                                                (boughtCrypto['boughtPrice'] * boughtCrypto['boughtAmt']) -
                                                                                (boughtCrypto['boughtFees'] + boughtCrypto['sellFees']))
                                        if(sell_price == boughtCrypto['boughtPrice'] + 
                                        ((boughtCrypto['boughtPrice'] - boughtCrypto['PULLBACK']) * 2)):                                                
                                            boughtCrypto['Up/Down'] = "UP"
                                        else:
                                            boughtCrypto['Up/Down'] = "DOWN"
                                        wallet['IN_POSITION'] = False
                                        wallet['COIN'] = ""
                                        wallet['ASSET_WORTH'] = 0.0
                                        if(sell_price == boughtCrypto['boughtPrice'] + 
                                        ((boughtCrypto['boughtPrice'] - boughtCrypto['PULLBACK']) * 2)):                                                
                                            wallet['win_trade'] += 1
                                        else:
                                            wallet['lose_trade'] += 1
                                else:
                                    if high > boughtCrypto['boughtPrice'] + (boughtCrypto['ATR'] * 4):
                                        sell_price = boughtCrypto['boughtPrice'] + (boughtCrypto['ATR'] * 4)
                                    elif low < boughtCrypto['boughtPrice'] - (boughtCrypto['ATR'] * 2):
                                        sell_price = boughtCrypto['boughtPrice'] - (boughtCrypto['ATR'] * 2)
                                    
                                    amount = boughtCrypto['boughtAmt']
                                    fees = (sell_price * amount) * 0.00075
                                    if sell_price != 0.0:
                                        virtual_wallet.sell_crypto(wallet, amount, sell_price, fees)

                                        boughtCrypto['sellPrice'] = sell_price
                                        boughtCrypto['sellAmt'] = amount
                                        boughtCrypto['sellTime'] = datetime.now()
                                        boughtCrypto['sellFees'] = fees
                                        boughtCrypto['Profit'] = ((boughtCrypto['sellPrice'] * boughtCrypto['sellAmt']) -
                                                                                (boughtCrypto['boughtPrice'] * boughtCrypto['boughtAmt']) -
                                                                                (boughtCrypto['boughtFees'] + boughtCrypto['sellFees']))
                                        if(sell_price == boughtCrypto['boughtPrice'] + (boughtCrypto['ATR'] * 4)):                                                
                                            boughtCrypto['Up/Down'] = "UP"
                                        else:
                                            boughtCrypto['Up/Down'] = "DOWN"
                                        wallet['IN_POSITION'] = False
                                        wallet['COIN'] = ""
                                        wallet['ASSET_WORTH'] = 0.0
                                        if(sell_price == boughtCrypto['boughtPrice'] + (boughtCrypto['ATR'] * 4)):                                                
                                            wallet['win_trade'] += 1
                                        else:
                                            wallet['lose_trade'] += 1
    except Exception as e:
        print(e)


start = datetime.now()

# short_listed_cryp = init()
virtual_wallet.init_wallet(wallet)
short_listed_cryp = ['TRXUSDT']
adx_bot(short_listed_cryp)
print(boughtCrypto)
print(wallet)
end = datetime.now()
print(end - start)



# def testone():
#     try:
#         crypto = 'COCOSUSDT'
#         kline = client.get_historical_klines(crypto, 
#                                                 Client.KLINE_INTERVAL_1DAY,
#                                                 DAY_CANDLES_PERIOD)
#         total_close = 0.0
#         kline_len = len(kline)
#         init_len = len(kline)
#         num_days = 0
#         ma = 0.0
#         ema_9 = 0.0
#         ema_12 = 0.0
#         ema_26 = 0.0
#         ema_50 = 0.0
#         ema_200 = 0.0
#         dailyEMA[crypto] = {}
#         print(init_len)

#         while kline_len > 0:
#             current_close = float(kline[-kline_len][4])
#             total_close += current_close
#             num_days += 1
#             if(init_len < 9):
#                 ma = ta_cal.cal_ema(total_close, current_close, num_days, init_len, ma)
#                 print(ma)
#             elif(init_len < 12):
#                 ema_9 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_9, ema_9)
#             elif(init_len < 26):
#                 ema_12 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_12, ema_12)
#             elif(init_len < 50):
#                 ema_26 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_26, ema_26)
#             elif(init_len < 200):
#                 ema_50 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_50, ema_50)
#             else:
#                 ema_200 = ta_cal.cal_ema(total_close, current_close, num_days, EMA_200, ema_200)

#             dailyEMA[crypto]['symbol'] = crypto
#             dailyEMA[crypto]['EMA'] = 0.0
            
#             if ema_200 != 0:
#                 dailyEMA[crypto]['EMA'] = ema_200
#             elif ema_50 != 0:
#                 dailyEMA[crypto]['EMA'] = ema_50
#             elif ema_26 != 0:
#                 dailyEMA[crypto]['EMA'] = ema_26
#             elif ema_12 != 0:
#                 dailyEMA[crypto]['EMA'] = ema_12
#             elif ema_9 != 0:
#                 dailyEMA[crypto]['EMA'] = ema_9
#             elif ma != 0:
#                 dailyEMA[crypto]['EMA'] = ma

#             kline_len -= 1
            
#     except Exception as e:
#         print("Error Calculating EMA")
#         print(e)