from XTBApi.exceptions import TransactionRejected
from XTBApi.api import Client
from classes.cache import Cache
from classes.profile import Param
import logging
LOGGER = logging.getLogger(__name__)


class Trade:
    """Xtb trade class."""
    def __init__(self, client, param):
        self.client: Client = client
        self.param: Param = param

    def trigger_open(self, symbol, mode='buy'):
        try:
            return self.client.open_trade(mode, symbol, self.param.volume,
                                          rate_tp=self.param.rate_tp, rate_sl=self.param.rate_sl)
        except TransactionRejected as e:
            return e

    def trigger_close(self, symbol, mode):
        self.client.update_trades()
        orders = {k: trans.order_id
                  for k, trans in self.client.trade_rec.items() if trans.symbol == symbol and trans.mode == mode}
        LOGGER.debug(f'Order to be closed: {orders}')
        res = {}
        for k, order_id in orders.items():
            try:
                res[k] = self.client.close_trade_only(order_id)
            except TransactionRejected as e:
                res[k] = f'Exception: {e}'
        return res

    def store_records(self, account):
        self.client.update_trades()
        if self.client.trade_rec:
            try:
                cur = {}
                new = {k: v.trans_dict for k, v in self.client.trade_rec.items()}
                cache = Cache()
                if cache.client.exists(f"trades_cur:{account}"):
                    cur = cache.get_key(f"trades_cur:{account}")
                cache.set_key(f"trades_pre:{account}", cur)
                cache.set_key(f"trades_cur:{account}", new)
            except ConnectionError as e:
                LOGGER.error(e)
