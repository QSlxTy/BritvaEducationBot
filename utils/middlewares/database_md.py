from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from integrations.database.sql_alch import Database
from src.bot.structures.data_structure import TransferData


class DatabaseMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: TransferData,
    ) -> Any:
        async with AsyncSession(bind=data['engine']) as session:
            data['db'] = Database(session)
            return await handler(event, data)
