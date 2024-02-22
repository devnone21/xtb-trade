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


class BtFx:
    def __init__(self, indicator: str, tech=None, candles=None):
        self.name = indicator.lower()
        self.tech = tech
        self.candles: DataFrame = candles
        self.df: DataFrame = candles

    def evaluate(self, candles: DataFrame):
        self.candles = self.df = candles
        # apply technical analysis (TA)
        self.df.ta.strategy(ta.Strategy(name=self.name, ta=self.tech))
        self.df.dropna(inplace=True, ignore_index=True)
        func = getattr(BtFx, f'_evaluate_{self.name}')
        return func(self)

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
        # apply
        self.df[['fx_type', 'fx_mode']] = DataFrame(
            self.df[[ca0, cb0, ca, cb]].apply(rsi_x, axis=1).values.tolist()
        )

    def _evaluate_stoch(self):
        """As evaluate function, takes DataFrame candles contains 'STOCHk...' column,
        return: (str)what_to_action, (str)mode_buy_or_sell.
        """
        def stoch_x(row):
            bits = row.values.tolist()
            if sum(bits) != 1:
                return {'fx_type': FXTYPE.STAY.value, 'fx_mode': FXMODE.NA.value}
            fx_type = FXTYPE.OPEN.value if bits[0] or bits[1] else FXTYPE.CLOSE.value
            fx_mode = FXMODE.BUY.value if bits[1] or bits[2] else FXMODE.SELL.value
            return {'fx_type': fx_type, 'fx_mode': fx_mode}

        self.name = 'stoch'
        # add signal
        cols = self.df.columns.to_list()
        col_stk = {'name': c for c in cols if c.startswith('STOCHk')}
        if not col_stk:
            return
        self.df = _add_signal(self.df, col_stk['name'], xa=80, xb=20)
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
        # extend columns with previous row's values
        self.df[ca0] = self.df[ca].shift()
        self.df[cb0] = self.df[cb].shift()
        # apply
        self.df[['fx_type', 'fx_mode']] = DataFrame(
            self.df[[ca0, cb0, ca, cb]].apply(stoch_x, axis=1).values.tolist()
        )
