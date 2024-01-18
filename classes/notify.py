from datetime import datetime
from pydantic import BaseModel
import logging
LOGGER = logging.getLogger(__name__)


class Notify(BaseModel):
    """Class of Notification messages."""
    ts: datetime = datetime.today()
    title: str = ''
    texts: str = ''
    lastmsg: str = ''

    def setts(self, ts: datetime) -> datetime:
        self.ts = ts
        return ts

    def add(self, message: str) -> str:
        self.texts += f'{message}\n'
        return message

    def print_notify(self, message: str) -> str:
        self.add(message)
        self.lastmsg = message
        LOGGER.info(message.strip())
        return message
