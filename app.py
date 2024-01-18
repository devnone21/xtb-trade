import time
from initial import *
from classes import Cache, Fx, Trade, Notify, Cloud
from XTBApi.api import Client
from redis.exceptions import ConnectionError
from datetime import datetime
from pandas import DataFrame


class Result:
    def __init__(self, symbol, app):
        self.symbol = symbol
        self.app = app
        self.market_status = False
        self.df = DataFrame()
        self.digits = 5
        self.epoch_ms = 0
        self.price = 0.0
        self.action = ''
        self.mode = ''

    def get_signal(self, client=None):
        logger = logging.getLogger(f'xtb.{self.app.name}')
        logger.setLevel(logging.DEBUG)
        x = self.app.param
        # get charts
        now = int(datetime.now().timestamp())
        res = client.get_chart_range_request(self.symbol, x.timeframe, now, now, -100) if client else {}
        digits = res.get('digits', 5)
        rate_infos = res.get('rateInfos', [])
        logger.debug(f'recv {self.symbol} {len(rate_infos)} ticks.')
        # caching
        try:
            cache = Cache()
            key_group = f'{x.account.mode}_{self.symbol}_{x.timeframe}'
            for ctm in rate_infos:
                cache.set_key(f'{key_group}:{ctm["ctm"]}', ctm)
            ctm_prefix = range(((now - x.timeframe*60*400) // 100_000), (now // 100_000)+1)
            rate_infos = []
            for pre in ctm_prefix:
                mkey = cache.client.keys(pattern=f'{key_group}:{pre}*')
                rate_infos.extend(cache.get_keys(mkey))
        except ConnectionError as e:
            logger.error(e)
        # prepare candles
        if not rate_infos:
            return
        rate_infos = [c for c in rate_infos if now - int(c['ctm'])/1000 > x.timeframe*60]
        rate_infos.sort(key=lambda by: by['ctm'])
        candles = DataFrame(rate_infos)
        candles['close'] = (candles['open'] + candles['close']) / 10 ** digits
        candles['high'] = (candles['open'] + candles['high']) / 10 ** digits
        candles['low'] = (candles['open'] + candles['low']) / 10 ** digits
        candles['open'] = candles['open'] / 10 ** digits
        logger.debug(f'got {self.symbol} {len(candles)} ticks.')
        # evaluate
        sign = Fx(indicator=x.indicator, tech=ind_presets.get(x.ind_preset))
        self.action, self.mode = sign.evaluate(candles)
        self.digits = digits
        self.df = sign.candles
        self.price = self.df.iloc[-1]['close']
        self.epoch_ms = self.df.iloc[-1]['ctm']


def run(app):
    logger = logging.getLogger(f'xtb.{app.name}')
    x = app.param
    # init chat notification
    report = Notify(title=f'[{app.name.upper()}-{x.account.name}]')
    # check if App's timing to be run
    if report.ts.minute % x.timeframe > 10:
        return False
    # Start here
    logger.debug(f'Running: {app.param}')
    # check App's breaker status
    if not x.breaker and x.account.mode == 'real':
        logger.debug('Breaker is OFF.')
        return False
    # start X connection
    client = Client()
    client.login(x.account.name, x.account.secret, mode=x.account.mode)
    logger.debug('Enter the Gate.')

    # Check if market is open
    market_status = client.get_market_status(x.symbols)
    logger.info(f'{report.title} Market status: {market_status}')
    tx = Trade(client=client, param=app.param)
    for symbol, status in market_status.items():
        if not status:
            continue

        # Market open, check signal
        r = Result(symbol, app)
        r.market_status = status
        r.get_signal(client=client)
        if not r.action:
            continue
        ts = report.setts(datetime.fromtimestamp(int(r.epoch_ms)/1000))
        report_ts = ts.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f'Signal: {symbol}, {r.action}, {r.mode.upper()}, {r.price} at {report_ts}')
        logger.debug(f'{symbol} - ' + r.df.tail(2).head(1).iloc[:, [0, 1, -4, -3, -2, -1]].to_string(header=False))
        logger.debug(f'{symbol} - ' + r.df.tail(1).iloc[:, [0, 1, -4, -3, -2, -1]].to_string(header=False))

        # Check signal to open/close transaction
        if r.action in ('open', 'close'):
            if r.action in ('open',):
                res = tx.trigger_open(symbol=symbol, mode=r.mode)
                report.print_notify(
                    f'>> {symbol}: Open-{r.mode.upper()} by {x.volume} at {report_ts}, {res}')
            elif r.action in ('close',):
                res = tx.trigger_close(symbol=symbol, mode=r.mode)
                report.print_notify(
                    f'>> {symbol}: Close-{r.mode.upper()} at {report_ts}, {res}')
            logger.info(report.lastmsg.strip())

    # store tx records in cache
    tx.store_records(x.account.name)
    client.logout()
    # stop conn, send chat notification
    gcp = Cloud()
    if report.texts:
        gcp.pub(f'{report.title}\n{report.texts}')

    return True


def demo():
    # loop through each App in profile settings
    for app in settings.profiles:
        # get and check App's account credential
        account: dict = accounts.get(app.param.account.name, {})
        if account:
            app.param.account.secret = account.get('pass', '')
            app.param.account.mode = account.get('mode', 'demo')
            if run(app):
                time.sleep(10)


if __name__ == '__main__':
    demo()
