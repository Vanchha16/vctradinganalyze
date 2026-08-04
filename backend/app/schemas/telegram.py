from datetime import datetime

from pydantic import BaseModel


class TelegramLinkResponse(BaseModel):
    link_code: str
    bot_username: str
    expires_at: datetime


class TelegramStatusResponse(BaseModel):
    linked: bool
    linked_at: datetime | None = None
