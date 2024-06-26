import time
from initial import settings, accounts, ind_presets
from classes import Cache, Fx, Trade, Notify, Cloud, Profile, FXTYPE, FXMODE
from XTBApi.api import Client
from XTBApi.exceptions import CommandFailed
from redis.exceptions import ConnectionError
from datetime import datetime
from pandas import DataFrame
import logging


class Result:
    def __init__(self, symbol: str, app: Profile, client: Client) -> None:
        self.symbol = symbol
        self.app = app
        self.client = client
        self.market_status = False
        self.df = DataFrame()
        self.candles = DataFrame()
        self.digits = 5
        self.epoch_ms = 0
        self.price = 0.0
        self.action = ''
        self.mode = ''
        self.inv_mode = ''

    def get_candles(self):
        logger = logging.getLogger(f'xtb.{self.app.name}')
        logger.setLevel(logging.DEBUG)
        x = self.app.param
        # get charts
        now = int(datetime.now().timestamp())
        res = self.client.get_chart_range_request(self.symbol, x.timeframe, now, now, -100) if self.client else {}
        digits = res.get('digits', 5)
        rate_infos = res.get('rateInfos', [])
        logger.debug(f'recv {self.symbol} {len(rate_infos)} ticks.')
        # caching
        try:
            cache = Cache()
            key_group = f'{x.account.mode}_{self.symbol}_{x.timeframe}'
            for ctm in rate_infos:
                cache.set_key(f'{key_group}:{ctm["ctm"]}', ctm, ttl_s=x.timeframe*172_800)
            ctm_prefix = range(((now - x.timeframe*60*400) // 100_000), (now // 100_000)+1)
            rate_infos = []
            for pre in ctm_prefix:
                mkey = cache.client.keys(pattern=f'{key_group}:{pre}*')
                rate_infos.extend(cache.get_keys(mkey))
        except ConnectionError as e:
            logger.error(e)
        # prepare candles
        if not rate_infos:
            return DataFrame()
        rate_infos = [c for c in rate_infos if now - int(c['ctm'])/1000 > x.timeframe*60]
        rate_infos.sort(key=lambda by: by['ctm'])
        candles = DataFrame(rate_infos)
        candles['close'] = (candles['open'] + candles['close']) / 10 ** digits
        candles['high'] = (candles['open'] + candles['high']) / 10 ** digits
        candles['low'] = (candles['open'] + candles['low']) / 10 ** digits
        candles['open'] = candles['open'] / 10 ** digits
        logger.debug(f'got {self.symbol} {len(candles)} ticks.')
        self.candles = candles
        self.digits = digits
        return candles

    def gen_signal(self, preset):
        x = self.app.param
        if not len(self.candles):
            return False
        # evaluate
        fx = Fx(indicator=x.indicator, tech=ind_presets.get(preset))
        fx.evaluate(self.candles)
        self.df = fx.df
        self.price = self.df.iloc[-1]['close']
        self.epoch_ms = self.df.iloc[-1]['ctm']
        self.action = FXTYPE(self.df.iloc[-1]['fx_type']).name.lower()
        self.mode = FXMODE(self.df.iloc[-1]['fx_mode']).name.lower()
        self.inv_mode = FXMODE(-1 * self.df.iloc[-1]['fx_mode']).name.lower()
        return True


def run(app):
    logger = logging.getLogger(f'xtb.{app.name}')
    x = app.param
    # init chat notification
    report = Notify(title=f'[{app.name.upper()}-{x.account.name}]')
    # check if App's timing to be run
    system_ts = datetime.today()
    if system_ts.minute % x.timeframe > 5:
        return False
    # Start here
    logger.debug(f'Running: {app.param}')
    # check App's breaker status
    if not x.breaker and not x.signal:
        logger.debug('Breaker is OFF.')
        return False
    # start X connection
    client = Client()
    try:
        client.login(x.account.name, x.account.secret, mode=x.account.mode)
    except CommandFailed:
        logger.debug('Gate is closed.')
        return False
    logger.debug('Enter the Gate.')

    # Check if market is open
    market_status = client.get_market_status(x.symbols)
    logger.info(f'{report.title} Market status: {market_status}')
    tx = Trade(client=client, param=app.param)
    for symbol, status in market_status.items():
        # Validate market status, signal and data timestamp
        r = Result(symbol, app, client=client)
        r.market_status = status
        r.get_candles()
        for preset in x.ind_preset:
            r.gen_signal(preset)
            data_ts = report.setts(datetime.fromtimestamp(int(r.epoch_ms)/1000))
            delta_ts = system_ts - data_ts
            if (not status) or (not r.action) or (delta_ts.seconds // 60 > x.timeframe + 5):
                continue
            report_time = data_ts.strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f'Signal: {symbol}, {r.action}, {r.mode.upper()}, {r.price} at {report_time}')
            debug_col_idx = [0, 1, 3, -7, -6, -5, -4, -3, -2, -1]
            logger.debug(f'{symbol} - ' + r.df.tail(2).head(1).iloc[:, debug_col_idx].to_string(header=False))
            logger.debug(f'{symbol} - ' + r.df.tail(1).iloc[:, debug_col_idx].to_string(header=False))

            # Check signal to open/close transaction
            if x.signal and r.action.lower() in ('open',):
                tech = ind_presets.get(preset)
                fast = tech[0].get('length')
                slow = tech[1].get('length')
                if r.mode.lower() in ('buy',):
                    report.print_notify(f'>> {symbol}: EMA {fast}/{slow} Cross-UP at {report_time}')
                    logger.info(report.lastmsg.strip())
                else:
                    report.print_notify(f'>> {symbol}: EMA {fast}/{slow} Cross-DOWN at {report_time}')
                    logger.info(report.lastmsg.strip())

            if x.breaker and r.action.lower() in ('open',):
                res = tx.trigger_open(symbol=symbol, mode=r.mode)
                report.print_notify(
                    f'>> {symbol}: Open-{r.mode.upper()} by {x.volume} at {report_time}, {res}')
                logger.info(report.lastmsg.strip())
            # elif r.action in ('close',):
                res = tx.trigger_close(symbol=symbol, mode=r.inv_mode)
                report.print_notify(
                    f'>> {symbol}: Close-{r.inv_mode.upper()} at {report_time}, {res}')
                logger.info(report.lastmsg.strip())

    # store tx records in cache
    tx.store_records(x.account.name)
    client.logout()
    # stop conn, send chat notification
    gcp = Cloud()
    if report.texts:
        gcp.pub(f'{report.title}\n{report.texts}')

    return True


def demo() -> None:
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
