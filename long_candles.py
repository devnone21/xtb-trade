import os
import json
import time
import logging.config
from classes import Settings, Cache, Profile
from XTBApi.api import Client
from redis.exceptions import ConnectionError
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

_logging_json = {
  "version": 1,
  "disable_existing_loggers": False,
  "formatters": {
    "default": {
      "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
      "datefmt": "%Y-%m-%d %H:%M:%S"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "default"
    },
    "rotating": {
      "class": "logging.handlers.TimedRotatingFileHandler",
      "formatter": "default",
      "filename": os.getenv("LOG_PATH", default="logs/app.log"),
      "when": "midnight",
      "backupCount": 3
    }
  },
  "loggers": {
    "": {
      "handlers": ["console"],
      "level": "CRITICAL",
      "propagate": True
    },
    "xtb": {
      "handlers": ["rotating"],
      "level": "DEBUG"
    }
  }
}
logging.config.dictConfig(_logging_json)

accounts: dict = json.load(open('account.json'))
profiles: list[Profile] = Settings(**json.load(open('settings.json'))).profiles


class Result:
    def __init__(self, symbol, app) -> None:
        self.symbol: str = symbol
        self.app: Profile = app
        self.market_status = False

    def get_candles(self, client=None):
        logger = logging.getLogger('xtb.long_candles')
        logger.setLevel(logging.DEBUG)
        x = self.app.param
        # get charts
        now = int(datetime.now().timestamp())
        res = client.get_chart_range_request(self.symbol, x.timeframe, now, now, -10_000) if client else {}
        rate_infos = res.get('rateInfos', [])
        logger.debug(f'recv {self.symbol} {len(rate_infos)} ticks.')
        # caching
        try:
            cache = Cache()
            key_group = f'{x.account.mode}_{self.symbol}_{x.timeframe}'
            for ctm in rate_infos:
                cache.set_key(f'{key_group}:{ctm["ctm"]}', ctm, ttl_s=x.timeframe*172_800)
        except ConnectionError as e:
            logger.error(e)


def run(app: Profile):
    logger = logging.getLogger('xtb.long_candles')
    x = app.param
    # Start here
    logger.debug(f'Running: {app.param}')
    # start X connection
    client = Client()
    client.login(x.account.name, x.account.secret, mode=x.account.mode)
    logger.debug('Enter the Gate.')

    # Check if market is open
    market_status = client.get_market_status(x.symbols)
    logger.info(f'[{app.name.upper()}-{x.account.name}] Market status: {market_status}')
    for symbol, status in market_status.items():
        if not status:
            continue

        # Market open, check signal
        r = Result(symbol, app)
        r.market_status = status
        r.get_candles(client=client)

    client.logout()
    return True


def demo() -> None:
    # loop through each App in profile settings
    for app in profiles:
        # get and check App's account credential
        account: dict = accounts.get(app.param.account.name, {})
        if account:
            app.param.account.secret = account.get('pass', '')
            app.param.account.mode = account.get('mode', 'demo')
            if run(app):
                time.sleep(10)


if __name__ == '__main__':
    demo()
