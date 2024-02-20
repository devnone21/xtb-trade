from dataclasses import dataclass, field
from itertools import count
from typing import Union, List
from classes import Profile


@dataclass
class Trade:
    order_id: int = field(default_factory=count(start=1).__next__, init=False)
    open_ctm: int
    symbol: str
    mode: int
    volume: Union[float, int]
    open_price: Union[float, int]
    close_ctm: Union[int, None] = None
    close_price: Union[float, int, None] = None
    pnl: Union[float, int] = 0.0
    closed: bool = False


@dataclass
class Orders:
    symbol: str
    digits: int
    volume: Union[float, int]
    records: List[Trade] = field(default_factory=list)

    def open_trade(self, mode: int, open_ctm: int, open_price: Union[float, int]) -> Trade:
        return Trade(open_ctm, self.symbol, mode, self.volume, open_price)

    def close_trade(self, mode: int, close_ctm: int, close_price: Union[float, int]):
        orders = [tx for tx in self.records if tx.mode == mode and not tx.closed]
        for tx in orders:
            tx.closed = True
            tx.close_ctm = close_ctm
            tx.close_price = close_price
            tx.pnl = (close_price - tx.open_price) * (10**self.digits) * tx.volume * mode
        return len(orders)


@dataclass
class Portfolio:
    profile: Profile
    order_group: List[Orders] = field(default_factory=list)
