from bt_initial import settings, symbol_digits, ind_presets
from bt_trades import Orders
from classes import Mongo, Profile, Fx, FXTYPE
from pandas import DataFrame
import pandas_ta as ta
import logging
logger = logging.getLogger('xtb.backtest')
add_tech = [
    {"kind": "bbands", "length": 20},
    {"kind": "ema", "length": 50}
]


class Result:
    def __init__(self, symbol: str, app: Profile):
        self.symbol = symbol
        self.app = app
        self.df = DataFrame()
        self.candles = DataFrame()
        digits = symbol_digits.get(symbol, 2)
        self.digits = digits
        self.orders = Orders(symbol, digits, volume=app.param.volume)

    def get_candles(self):
        x = self.app.param
        rate_infos = []
        # Start DB connection
        db = Mongo(db='xtb')
        key_group = f'real_{self.symbol}_{x.timeframe}'
        rate_infos.extend(db.find_all(key_group))
        db.client.close()
        # prepare candles
        logger.debug(f'GetCD: {len(rate_infos)} ticks')
        if not rate_infos:
            return DataFrame()
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
        if not len(candles):
            return False
        # pre-analysis
        candles.ta.strategy(ta.Strategy(name='Bt', ta=add_tech))
        # evaluate
        fx = Fx(indicator=x.indicator, tech=ind_presets.get(x.ind_preset))
        fx.evaluate(candles)
        logger.debug(f'GenFX: shape is {fx.df.shape}')
        self.df = fx.df
        return True

    def sim_trades(self):
        self.df['order_id'] = 0
        for i, row in self.df.iterrows():
            if row['fx_type'] == FXTYPE.OPEN.value:
                tx = self.orders.open_trade(
                    mode=int(row['fx_mode']),
                    open_ctm=int(row['ctm']),
                    open_price=row['close']
                )
                self.orders.records.append(tx)
                self.df.at[i, 'order_id'] = tx.order_id
            if row['fx_type'] == FXTYPE.CLOSE.value:
                self.orders.close_trade(
                    mode=int(row['fx_mode']),
                    close_ctm=int(row['ctm']),
                    close_price=row['close']
                )
        self.orders.eval_performance()
        # self.df.to_csv(f'df_{self.symbol}_{self.app.param.timeframe}.csv', index=False)

    def merge_orders_df(self):
        """extend df with orders"""
        df = self.df.merge(self.orders.df, how='left', on='order_id', indicator=True)

        # export df in csv/feather
        df.to_csv(f'df_{self.symbol}_{self.app.param.timeframe}.csv', index=False)

        selected_cols = [
            "order_id", "cmd", "volume", "open_price", "close_price", "profit", "cum_profit",
            "open_ctm", "close_ctm", "open_time", "close_time",
        ]
        self.orders.df[selected_cols].to_csv(f'orders_{self.symbol}_{self.app.param.timeframe}.csv', index=False)


def run(app: Profile):
    x = app.param
    perf = []
    for symbol in x.symbols:
        r = Result(symbol, app)
        if r.gen_signal():
            r.sim_trades()
            r.merge_orders_df()
        perf.append(r.orders.performance)
    DataFrame(perf, index=[f'{s}_{x.timeframe}' for s in x.symbols])\
        .to_csv(f'perf_{app.name}.csv')


if __name__ == '__main__':
    # loop through each App in profile settings
    for profile in settings.profiles:
        logger.debug(f'Running: {profile}')
        run(profile)
