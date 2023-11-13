from XTBApi.api import Client
from XTBApi.exceptions import TransactionRejected

usr = ("15351881", "wx+-jLk*9Be!a%*")

def trigger_update_price():
    return

def trigger_notify():
    return

def trigger_open_trade(symbol):
    # mode, symbol, volume = ('buy', 'EURUSD', 1)
    try:
        client.open_trade(mode='buy', symbol=symbol, volume=1)
    except TransactionRejected:
        # May send notification
        trigger_notify()
    return

# Initial connection
client = Client()
client.login(usr[0], usr[1], mode='real')

# Check if market is open for the symbol
market_status = client.check_if_market_open(['GOLD', 'EURUSD'])
for symbol in market_status.keys():
    # trigger_update_price()
    # if market_status[symbol]:
    trigger_open_trade(symbol)

client.logout()


# # BUY ONE VOLUME (FOR EURUSD THAT CORRESPONDS TO 100000 units)
# client.open_trade('buy', 'EURUSD', 1)
# # SEE IF ACTUAL GAIN IS ABOVE 100 THEN CLOSE THE TRADE
# trades = client.update_trades() # GET CURRENT TRADES
# trade_ids = [trade_id for trade_id in trades.keys()]
# for trade in trade_ids:
#     actual_profit = client.get_trade_profit(trade) # CHECK PROFIT
#     if actual_profit >= 100:
#         client.close_trade(trade) # CLOSE TRADE
# # CLOSE ALL OPEN TRADES
# client.close_all_trades()
# # THEN LOGOUT
# client.logout()
