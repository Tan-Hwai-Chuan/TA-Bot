# Calculate exponential moving average
def cal_ema(total_close, curr_close, curr_day, period, prev_ema):
    ema = 0.0
    weight_ratio = 2 / (period + 1)
    if curr_day == period:
        ema = total_close/period
    elif curr_day > period:
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

def wilder_first_smoothing(curr_value, prev_value, indicator_period):
    smoothed_value = prev_value - (prev_value/indicator_period) + curr_value

    return smoothed_value

def wilder_second_smoothing(curr_value, prev_value, indicator_period):
    smoothed_value = ((prev_value * (indicator_period - 1)) + curr_value) / indicator_period

    return smoothed_value

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

# Calculate MACD
def cal_macd(ema12, ema26):
    return ema12 - ema26

def first_period_total(array):
    total = 0.0
    for indicator in array:
        total = total + indicator

    return total

def insert_till_max(array, new_value, indicator_period, return_first_value=False):
    if len(array) < indicator_period:
        array.append(new_value)
    else: 
        array.append(new_value)
        first_value = array.pop(0)
        if(return_first_value == True):
            return first_value


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