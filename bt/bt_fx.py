from pandas import DataFrame, concat
from pandas_ta.utils import signals as ta_signals
import pandas_ta as ta


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
    def __init__(self, tech=None):
        self.tech = tech
        self.candles: DataFrame = DataFrame()
        self.df: DataFrame = DataFrame()

    def analysis(self, candles: DataFrame):
        self.candles = candles.copy()
        self.df = candles.copy()
        # apply technical analysis (TA)
        self.df.ta.strategy(ta.Strategy(name='Bt', ta=self.tech))
        self.df.dropna(inplace=True, ignore_index=True)
