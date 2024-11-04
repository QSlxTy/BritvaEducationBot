from typing import TypedDict

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncEngine


class TransferData(TypedDict):
    engine: AsyncEngine