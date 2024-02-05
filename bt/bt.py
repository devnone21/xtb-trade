from bt_initial import *
from bt_fx import BtFx, FXTYPE
from bt_trades import Orders
from classes import Cache, Profile
from redis.exceptions import ConnectionError
from datetime import datetime
from pandas import DataFrame
import logging
logging.basicConfig(
     filename='bt.log',
     level=logging.DEBUG,
     format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
     datefmt='%Y-%m-%d %H:%M:%S'
 )


class Result:
    def __init__(self, symbol: str, app: Profile):
        self.symbol = symbol
        self.app = app
        self.df = DataFrame()
        self.candles = DataFrame()
        self.digits = symbol_digits.get(symbol, 2)
        self.orders = Orders(symbol, volume=app.param.volume)

    def get_candles(self):
        x = self.app.param
        rate_infos = []
        try:
            cache = Cache()
            key_group = f'real_{self.symbol}_{x.timeframe}'
            mkey = cache.client.keys(pattern=f'{key_group}:*')
            rate_infos.extend(cache.get_keys(mkey))
        except ConnectionError as e:
            logging.error(e)
        # prepare candles
        logging.debug(f'GetCD: {len(rate_infos)} ticks')
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
        fx = BtFx(indicator=x.indicator, tech=ind_presets.get(x.ind_preset))
        fx.evaluate(candles)
        logging.debug(f'GenFX: shape is {fx.df.shape}')
        self.df = fx.df

    def sim_trades(self):
        for row in self.df:
            if row['fx_type'] == FXTYPE.OPEN.value:
                tx = self.orders.open_trade(
                    mode=int(row['fx_mode']),
                    open_dt=datetime.fromtimestamp(int(row['ctm']) / 1000),
                    open_price=row['close']
                )
                self.orders.records.append(tx)
                row['order_id'] = tx.id
            if row['fx_type'] == FXTYPE.CLOSE.value:
                self.orders.close_trade(
                    mode=int(row['fx_mode']),
                    close_dt=datetime.fromtimestamp(int(row['ctm']) / 1000),
                    close_price=row['close']
                )
        logging.debug(f'SimOrders: {len(self.orders.records)}')

    def merge_orders_df(self):
        """extend df with orders"""
        orders_df = DataFrame([tx.__dict__ for tx in self.orders.records])
        selected_cols = ["id", "mode", "volume", "close_dt", "close_price", "pnl"]
        # self.df.merge(orders_df[selected_cols], how='left', left_on='order_id', right_on='id')
        orders_df[selected_cols].to_feather(f'orders_{self.app.name}_{self.symbol}.ftr')

    def store_final_df(self):
        """store df in feather"""
        self.df.to_feather(f'df_{self.app.name}_{self.symbol}.ftr')


def run(app: Profile):
    x = app.param
    for symbol in x.symbols:
        r = Result(symbol, app)
        r.gen_signal()
        r.sim_trades()
        r.merge_orders_df()
        r.store_final_df()


if __name__ == '__main__':
    # loop through each App in profile settings
    for profile in settings.profiles:
        logging.debug(f'Running: {profile}')
        run(profile)
