from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Awaitable, Union

from aiogram import BaseMiddleware, types
from aiogram.types import Message, CallbackQuery
from sqlalchemy.exc import NoResultFound

from integrations.database.models.policy_status import get_learning_status
from integrations.database.models.user import get_user


class AccessCheck(BaseMiddleware):
    def __init__(self):
        pass

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Union[Message, CallbackQuery],
            data: Dict[str, Any]
    ) -> Any:
        session_maker = data['session_maker']
        user_info = await get_user(event.from_user.id, session_maker)
        if user_info.access is True:
            try:
                policy_info = await get_learning_status(event.from_user.id, session_maker)
                if user_info.is_admin is False:
                    if datetime.now() - policy_info.date_start >= timedelta(days=3):
                        if isinstance(event, types.Message):
                            await event.answer('<b>У вас закончилось время для доступа к курсу</b>')
                        else:
                            await event.answer('У вас закончилось время для доступа к курсу')
                    else:
                        return await handler(event, data)
                else:
                    return await handler(event, data)
            except NoResultFound:
                return await handler(event, data)
        else:
            if isinstance(event, types.Message):
                await event.answer('<b>У вас нет доступа к курсу</b>')
            else:
                await event.answer('У вас нет доступа к курсу')
