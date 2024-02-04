from bt_initial import *
from classes import Cache, Fx, Profile
from redis.exceptions import ConnectionError
from datetime import datetime
from pandas import DataFrame
import logging
logging.basicConfig(
     filename='backtest.log',
     level=logging.INFO,
     format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
     datefmt='%Y-%m-%d %H:%M:%S'
 )


class Result:
    def __init__(self, symbol, app):
        self.symbol = symbol
        self.app = app
        self.df = DataFrame()
        self.candles = DataFrame()
        self.digits = symbol_digits.get(self.symbol, 2)
        self.epoch_ms = 0
        self.price = 0.0
        self.action = ''
        self.mode = ''

    def get_candles(self):
        x = self.app.param
        rate_infos = []
        try:
            cache = Cache()
            key_group = f'{x.account.mode}_{self.symbol}_{x.timeframe}'
            mkey = cache.client.keys(pattern=f'{key_group}:*')
            rate_infos.extend(cache.get_keys(mkey))
        except ConnectionError as e:
            logging.error(e)
        # prepare candles
        if not rate_infos:
            return
        rate_infos.sort(key=lambda by: by['ctm'])
        candles = DataFrame(rate_infos)
        candles['close'] = (candles['open'] + candles['close']) / 10 ** self.digits
        candles['high'] = (candles['open'] + candles['high']) / 10 ** self.digits
        candles['low'] = (candles['open'] + candles['low']) / 10 ** self.digits
        candles['open'] = candles['open'] / 10 ** self.digits
        self.candles = candles
        return candles

    def gen_signal(self):
        x = self.app.param
        candles = self.get_candles()
        # evaluate
        fx = Fx(indicator=x.indicator, tech=ind_presets.get(x.ind_preset))
        self.action, self.mode = fx.evaluate(candles)
        self.df = fx.candles
        self.price = self.df.iloc[-1]['close']
        self.epoch_ms = self.df.iloc[-1]['ctm']


def run(app: Profile):
    x = app.param

    # Start here
    for symbol in x.symbols:
        r = Result(symbol, app)
        r.get_candles()
        ts = datetime.fromtimestamp(int(r.epoch_ms)/1000)
        report_ts = ts.strftime("%Y-%m-%d %H:%M:%S")

    # store tx records in cache
    # tx.store_records(x.account.name)

    return True


if __name__ == '__main':
    # loop through each App in profile settings
    for profile in settings.profiles:
        run(profile)
