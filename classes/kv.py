import os
from requests import get
from pydantic import BaseModel


class KV(BaseModel):
    """Class of CF KV storage api."""
    url: str = 'http://localhost'
    result: dict = {}

    def query(self) -> dict:
        if not os.getenv("KV_HOST"):
            return self.result

        self.url = f'{os.getenv("KV_HOST")}?k={os.getenv("KV_TOKEN")}'
        res = get(self.url)
        self.result = res.json()
        return self.result
