from dataclasses import dataclass


@dataclass
class Account:
    name: str
    mode: str = 'demo'
    secret: str = ''

    def __str__(self):
        return f'{self.__class__.__name__}({self.name}, {self.mode})'

    def __repr__(self):
        return self.__str__()


@dataclass
class Param:
    account: str | dict | Account
    breaker: bool
    symbols: list[str]
    timeframe: int
    volume: float
    rate_tp: float | int
    rate_sl: float | int
    indicator: str
    ind_preset: str

    def __post_init__(self):
        self.account = Account(self.account)


@dataclass
class Profile:
    name: str
    param: dict | Param

    def __post_init__(self):
        self.param = Param(**self.param)


@dataclass
class Settings:
    rayId: str
    _comment: str
    profiles: list[dict] | list[Profile]

    def __post_init__(self):
        self.profiles = [Profile(**p) for p in self.profiles]
