from dataclasses import dataclass, field
from itertools import count
from typing import Union
from classes import Profile
from datetime import datetime


@dataclass
class Trade:
    order_id: int = field(default_factory=count(start=1).__next__, init=False)
    open_dt: datetime
    symbol: str
    mode: int
    volume: Union[float, int]
    open_price: Union[float, int]
    close_dt: Union[datetime, None] = None
    close_price: Union[float, int, None] = None
    pnl: Union[float, int] = 0.0
    closed: bool = False


@dataclass
class Orders:
    symbol: str
    volume: Union[float, int]
    records: list[Trade] = field(default_factory=list)

    def open_trade(self, mode: int, open_dt: datetime, open_price: float | int) -> Trade:
        return Trade(open_dt, self.symbol, mode, self.volume, open_price)

    def close_trade(self, mode: int, close_dt: datetime, close_price: float | int):
        orders = [tx for tx in self.records if tx.mode == mode and not tx.closed]
        for tx in orders:
            tx.closed = True
            tx.close_dt = close_dt
            tx.close_price = close_price
            tx.pnl = (close_price - tx.open_price) * tx.volume * mode
        return len(orders)


@dataclass
class Portfolio:
    profile: Profile
    order_group: list[Orders] = field(default_factory=list)
