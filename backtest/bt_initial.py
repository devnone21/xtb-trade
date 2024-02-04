import os
import json
from enum import Enum
from classes import Settings
from dotenv import load_dotenv
load_dotenv()


class MODES(Enum):
    BUY = 0
    SELL = 1


settings = Settings(**json.load(open('settings.json')))
ind_presets = {
  "TA_RSI_L14_XA70_XB30": [
        {
            "kind": "rsi", "length": 14, "signal_indicators": True,
            "xa": 70, "xb": 30
        }
  ],
  "TA_RSI_L14_XA65_XB35": [
        {
            "kind": "rsi", "length": 14, "signal_indicators": True,
            "xa": 65, "xb": 35
        }
  ],
  "TA_STOCH_K14_XA80_XB20": [
        {
            "kind": "stoch", "k": 14, "d": 3, "smooth_k": 3,
            "xa": 80, "xb": 20
        }
  ],
}
symbol_digits = {
    "GOLD": 2,
    "GOLD.FUT": 2,
    "OIL.WTI": 2,
    "EURUSD": 5,
    "SILVER": 3,
}

if __name__ == '__main__':
    print(settings.profiles)
    print(os.getenv("REDIS_HOST"))
