from dataclasses import dataclass
from typing import Union
from datetime import datetime


@dataclass
class Trades:
    id: int
    open_dt: datetime
    close_dt: datetime
    symbol: str
    mode: str
    volume: Union[float, int]
    open_price: Union[float, int]
    close_price: Union[float, int]
    pnl: Union[float, int]
    closed: bool
