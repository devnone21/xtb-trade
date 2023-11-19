import json
import time
from datetime import datetime

from websocket import create_connection
from websocket._exceptions import WebSocketConnectionClosedException

LOGIN_TIMEOUT = 120
MAX_TIME_INTERVAL = 0.200


def _get_data(command, **parameters):
    data = {
        "command": command,
    }
    if parameters:
        data['arguments'] = {}
        for (key, value) in parameters.items():
            data['arguments'][key] = value
    return data


class BaseClient(object):
    """main client class"""

    def __init__(self):
        self.ws = None
        self._login_data = None
        self._time_last_request = time.time() - MAX_TIME_INTERVAL

    def _send_command(self, dict_data):
        """send command to api"""
        time_interval = time.time() - self._time_last_request
        if time_interval < MAX_TIME_INTERVAL:
            time.sleep(MAX_TIME_INTERVAL - time_interval)
        try:
            self.ws.send(json.dumps(dict_data))
            response = self.ws.recv()
        except WebSocketConnectionClosedException:
            print('SocketError')
        self._time_last_request = time.time()
        res = json.loads(response)
        if res['status'] is False:
            print(f'CommandFailed: {res}')
        if 'returnData' in res.keys():
            return res['returnData']

    def login(self, user_id, password, mode='demo'):
        """login command"""
        data = _get_data("login", userId=user_id, password=password)
        self.ws = create_connection(f"wss://ws.xtb.com/{mode}")
        response = self._send_command(data)
        self._login_data = (user_id, password)
        return response

    def logout(self):
        """logout command"""
        data = _get_data("logout")
        response = self._send_command(data)
        return response

    def get_chart_range_request(self, symbol, period, start, end, ticks=0):
        """getChartRangeRequest command"""
        if not isinstance(ticks, int):
            raise ValueError(f"ticks value {ticks} must be int")
        args = {
            "symbol": symbol,
            "period": period,
            "start": start * 1000,
            "end": end * 1000,
            "ticks": ticks
        }
        data = _get_data("getChartRangeRequest", info=args)
        return self._send_command(data)

    def get_trading_hours(self, trade_position_list):
        """getTradingHours command"""
        data = _get_data("getTradingHours", symbols=trade_position_list)
        response = self._send_command(data)
        for symbol in response:
            for day in symbol['trading']:
                day['fromT'] = int(day['fromT'] / 1000)
                day['toT'] = int(day['toT'] / 1000)
            for day in symbol['quotes']:
                day['fromT'] = int(day['fromT'] / 1000)
                day['toT'] = int(day['toT'] / 1000)
        return response

    def get_symbol(self, symbol):
        """getSymbol command"""
        data = _get_data("getSymbol", symbol=symbol)
        return self._send_command(data)

    def trade_transaction(self, symbol, mode, trans_type, volume, stop_loss=0,
                          take_profit=0, **kwargs):
        """tradeTransaction command"""
        # check type
        if trans_type not in [x.value for x in TRANS_TYPES]:
            raise ValueError(f"Type must be in {[x for x in trans_type]}")
        # check sl & tp
        stop_loss = float(stop_loss)
        take_profit = float(take_profit)
        # check kwargs
        accepted_values = ['order', 'price', 'expiration', 'customComment',
                           'offset', 'sl', 'tp']
        assert all([val in accepted_values for val in kwargs.keys()])
        info = {
            'cmd': mode,
            'symbol': symbol,
            'type': trans_type,
            'volume': volume,
            'sl': stop_loss,
            'tp': take_profit
        }
        info.update(kwargs)  # update with kwargs parameters
        data = _get_data("tradeTransaction", tradeTransInfo=info)
        return self._send_command(data)


class Client(BaseClient):
    """advanced class of client"""
    def __init__(self):
        super().__init__()
        self.trade_rec = {}

    def check_if_market_open(self, list_of_symbols):
        """check if market is open for symbol in symbols"""
        _td = datetime.today()
        actual_tmsp = _td.hour * 3600 + _td.minute * 60 + _td.second
        response = self.get_trading_hours(list_of_symbols)
        market_values = {}
        for symbol in response:
            today_values = [day for day in symbol['trading'] if day['day'] ==
                _td.isoweekday()]
            if not today_values:
                market_values[symbol['symbol']] = False
                continue
            today_values = today_values[0]
            if today_values['fromT'] <= actual_tmsp <= today_values['toT']:
                market_values[symbol['symbol']] = True
            else:
                market_values[symbol['symbol']] = False
        return market_values

    def open_trade(self, mode, symbol, volume):
        """open trade transaction"""
        if mode in [MODES.BUY.value, MODES.SELL.value]:
            mode = [x for x in MODES if x.value == mode][0]
        elif mode in ['buy', 'sell']:
            modes = {'buy': MODES.BUY, 'sell': MODES.SELL}
            mode = modes[mode]
        else:
            raise ValueError("mode can be buy or sell")
        mode_name = mode.name
        mode_value = mode.value
        conversion_mode = {MODES.BUY.value: 'ask', MODES.SELL.value: 'bid'}
        price = self.get_symbol(symbol)[conversion_mode[mode_value]]
        response = self.trade_transaction(symbol, mode_value, 0, volume, price=price)
        return response
 