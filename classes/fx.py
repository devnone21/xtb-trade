from pandas import DataFrame, concat
from pandas_ta.utils import signals as ta_signals
from enum import Enum
import pandas_ta as ta


class FXTYPE(Enum):
    OPEN = 1
    CLOSE = -1
    STAY = 0


class FXMODE(Enum):
    BUY = 1
    SELL = -1
    NA = 0


def _add_signal(df: DataFrame, ind_name: str, **kwargs) -> DataFrame:
    ind = df[ind_name]
    signalsdf = concat(
        [
            df,
            ta_signals(
                indicator=ind,
                xa=kwargs.pop("xa", 80),
                xb=kwargs.pop("xb", 20),
                xserie=kwargs.pop("xserie", None),
                xserie_a=kwargs.pop("xserie_a", None),
                xserie_b=kwargs.pop("xserie_b", None),
                cross_values=kwargs.pop("cross_values", False),
                cross_series=kwargs.pop("cross_series", True),
                offset=None,
            ),
        ],
        axis=1,
    )
    return signalsdf


class Fx:
    def __init__(self, indicator: str, tech=None, candles=None):
        self.name = indicator.lower()
        self.tech = tech
        self.candles: DataFrame = candles
        self.df: DataFrame = candles

    def evaluate(self, candles: DataFrame):
        self.candles = candles.copy()
        self.df = candles.copy()
        # apply technical analysis (TA)
        self.df.ta.strategy(ta.Strategy(name=self.name, ta=self.tech))
        self.df.dropna(inplace=True, ignore_index=True)
        func = getattr(Fx, f'_evaluate_{self.name}')
        return func(self)

    def _evaluate_emax(self):
        """As evaluate function, takes DataFrame candles contains 'EMA...' column,
        return: (str)what_to_action, (str)mode_buy_or_sell.
        """
        def ema_x(row):
            f1, s1, f2, s2 = row.values.tolist()
            if f1 > s1 and f2 < s2:
                return {'fx_type': FXTYPE.OPEN.value, 'fx_mode': FXMODE.SELL.value}
            if f1 < s1 and f2 > s2:
                return {'fx_type': FXTYPE.OPEN.value, 'fx_mode': FXMODE.BUY.value}
            return {'fx_type': FXTYPE.STAY.value, 'fx_mode': FXMODE.NA.value}

        self.name = 'emax'
        cols = self.df.columns.to_list()
        cols_ema = [c for c in cols if c.startswith('EMA')]
        if len(cols_ema) != 2:
            return
        ca = cols_ema[0]
        cb = cols_ema[-1]
        ca0 = 'prev' + ca
        cb0 = 'prev' + cb
        # extend columns with previous row's values
        self.df[ca0] = self.df[ca].shift()
        self.df[cb0] = self.df[cb].shift()
        self.df.dropna(inplace=True, ignore_index=True)
        # apply
        self.df[['fx_type', 'fx_mode']] = DataFrame(
            self.df[[ca0, cb0, ca, cb]].apply(ema_x, axis=1).values.tolist()
        )

    def _evaluate_macd(self):
        """As evaluate function, takes DataFrame candles contains 'MACD..._XA_0' column,
        return: (str)what_to_action, (str)mode_buy_or_sell.
        """
        def macd_x(row):
            xa, xb = row.values.tolist()
            if xa:
                return {'fx_type': FXTYPE.OPEN.value, 'fx_mode': FXMODE.BUY.value}
            if xb:
                return {'fx_type': FXTYPE.OPEN.value, 'fx_mode': FXMODE.SELL.value}
            return {'fx_type': FXTYPE.STAY.value, 'fx_mode': FXMODE.NA.value}

        self.name = 'macd'
        cols = self.df.columns.to_list()
        col_xa = {'name': c for c in cols if c.startswith('MACD') and ('_XA_' in c)}
        col_xb = {'name': c for c in cols if c.startswith('MACD') and ('_XB_' in c)}
        if not col_xa or not col_xb:
            return
        ca = col_xa['name']
        cb = col_xb['name']
        # apply
        self.df.dropna(inplace=True, ignore_index=True)
        self.df[['fx_type', 'fx_mode']] = DataFrame(
            self.df[[ca, cb]].apply(macd_x, axis=1).values.tolist()
        )

    def _evaluate_rsi(self):
        """As evaluate function, takes DataFrame candles contains 'RSI..._A_' or 'RSI..._B_' column,
        return: (str)what_to_action, (str)mode_buy_or_sell.
        """
        def rsi_x(row):
            bits = row.values.tolist()
            if sum(bits) != 1:
                if "".join((str(i) for i in bits)) == '0110':
                    return {'fx_type': FXTYPE.CLOSE.value, 'fx_mode': FXMODE.BUY.value}
                if "".join((str(i) for i in bits)) == '1001':
                    return {'fx_type': FXTYPE.CLOSE.value, 'fx_mode': FXMODE.SELL.value}
                return {'fx_type': FXTYPE.STAY.value, 'fx_mode': FXMODE.NA.value}
            fx_type = FXTYPE.OPEN.value if bits[0] or bits[1] else FXTYPE.CLOSE.value
            fx_mode = FXMODE.BUY.value if bits[1] or bits[2] else FXMODE.SELL.value
            return {'fx_type': fx_type, 'fx_mode': fx_mode}

        self.name = 'rsi'
        cols = self.df.columns.to_list()
        col_a = {'name': c for c in cols if c.startswith('RSI') and ('_A_' in c)}
        col_b = {'name': c for c in cols if c.startswith('RSI') and ('_B_' in c)}
        if not col_a or not col_b:
            return
        ca = col_a['name']
        ca0 = 'prev' + ca
        cb = col_b['name']
        cb0 = 'prev' + cb
        # extend columns with previous row's values
        self.df[ca0] = self.df[ca].shift()
        self.df[cb0] = self.df[cb].shift()
        self.df.dropna(inplace=True, ignore_index=True)
        # apply
        self.df[['fx_type', 'fx_mode']] = DataFrame(
            self.df[[ca0, cb0, ca, cb]].apply(rsi_x, axis=1).values.tolist()
        )

    def _evaluate_stoch(self):
        """As evaluate function, takes DataFrame candles contains 'STOCHk...' column,
        return: (str)what_to_action, (str)mode_buy_or_sell.
        """
        def kd_cross(values: list) -> bool:
            k0, d0, k, d = values
            return (k0-d0)*(k-d) < 0

        def stoch_x(row):
            bits = row.values.tolist()[-4:]
            vals = row.values.tolist()[:4]
            # SO scenarios and crossover
            stk_scene = "".join([str(int(i)) for i in bits])
            if stk_scene in ('0001', '1000', '1001'):
                return {'fx_type': FXTYPE.CLOSE.value, 'fx_mode': FXMODE.BUY.value}
            if stk_scene in ('0010', '0100', '0110'):
                return {'fx_type': FXTYPE.CLOSE.value, 'fx_mode': FXMODE.SELL.value}
            if stk_scene in ('0101',) and kd_cross(vals):
                return {'fx_type': FXTYPE.OPEN.value, 'fx_mode': FXMODE.BUY.value}
            if stk_scene in ('1010',) and kd_cross(vals):
                return {'fx_type': FXTYPE.OPEN.value, 'fx_mode': FXMODE.SELL.value}
            # Other scenarios
            # return {'fx_type': stk_scene, 'fx_mode': kd_cross(vals)}
            return {'fx_type': FXTYPE.STAY.value, 'fx_mode': FXMODE.NA.value}

        self.name = 'stoch'
        # add signal
        cols = self.df.columns.to_list()
        col_stk = {'name': c for c in cols if c.startswith('STOCHk')}
        col_std = {'name': c for c in cols if c.startswith('STOCHd')}
        if not col_stk or not col_std:
            return
        tech_so = [d for d in self.tech if d['kind'] == 'stoch'][0]
        self.df = _add_signal(self.df, col_stk['name'], **tech_so)
        # actual evaluate
        cols = self.df.columns.to_list()
        col_a = {'name': c for c in cols if c.startswith('STOCH') and ('_A_' in c)}
        col_b = {'name': c for c in cols if c.startswith('STOCH') and ('_B_' in c)}
        if not col_a or not col_b:
            return
        ca = col_a['name']
        ca0 = 'prev' + ca
        cb = col_b['name']
        cb0 = 'prev' + cb
        ck = col_stk['name']
        ck0 = 'prev' + ck
        cd = col_std['name']
        cd0 = 'prev' + cd
        # extend columns with previous row's values
        self.df[ca0] = self.df[ca].shift()
        self.df[cb0] = self.df[cb].shift()
        self.df[ck0] = self.df[ck].shift()
        self.df[cd0] = self.df[cd].shift()
        self.df.dropna(inplace=True, ignore_index=True)
        # apply
        self.df[['fx_type', 'fx_mode']] = DataFrame(
            self.df[[ck0, cd0, ck, cd, ca0, cb0, ca, cb]].apply(stoch_x, axis=1).values.tolist()
        )
