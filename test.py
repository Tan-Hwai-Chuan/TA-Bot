from binance.client import Client
from binance.enums import *
from numpy import true_divide
import config
import sys

def find_pullback(closes, low_prices):
    last_index = -1
    lowest_close = 0
    
    while -(last_index) < len(closes):
        if(closes[last_index] > closes[last_index - 1]):
            lowest_close = low_prices[last_index - 1]
            last_index -= 1
        else:
            return lowest_close

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
    print(len(closes))

    while -(last_index) < len(closes):
        if(descending):
            if(closes[last_index] <= closes[last_index - 1]):
                result_array.append({'H/L':'L','index':last_index})
                descending = False
            last_index -= 1
            print(last_index)
        elif(not descending):
            if(closes[last_index] >= closes[last_index - 1]):
                result_array.append({'H/L':'H','index':last_index})
                descending = True
            last_index -= 1
            print(last_index)

    return result_array
    
    


arr = [1,2,3,4,5]
arr1 = [1,2,3,5,4]
arr2 = [53,3,4,5]
arr3 = [5,3,4,2,1]
arr4 = [4,1,2,3,5]
arr5 = [1,2,3,4,5,4,3,2,4,5,6,7,8,9,10,3,5,2,8,4,9]
larr = [0,1,2,3,4,3,2,1,3,4,5,6,7,8,9,2,4,1,7,3,8]

empty = []

empty = find_peak_trough(arr5,empty)
testarr = [1,2,3,4,5,6,7,8,9]

print(testarr[4:len(testarr)])
# print(sys.getrecursionlimit())

# print(larr[testarr[0]['index']])
# print(find_pullback(arr,arr))
# print(find_pullback(arr1,arr1))
# print(find_pullback(arr2,arr2))