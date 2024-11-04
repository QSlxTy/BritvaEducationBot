from typing import Callable, Dict, Any, Awaitable, Union

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from integrations.database.models.user import is_user_exists, create_user, get_user
from keyboards.admin.admin_keyboard import admin_topic_kb
from src.config import conf


class RegisterCheck(BaseMiddleware):
    def __init__(self):
        pass

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Union[Message, CallbackQuery],
            data: Dict[str, Any]
    ) -> Any:
        if data.get('session_maker'):
            session_maker = data['session_maker']
            if not await is_user_exists(user_id=event.from_user.id, session_maker=session_maker):
                topic_id = await event.bot.create_forum_topic(int(conf.admin_topic),
                                                              f'{event.from_user.full_name} [ID{event.from_user.id}]')
                await create_user(event.from_user.id, event.from_user.username, int(topic_id.message_thread_id),
                                  event.from_user.first_name,
                                  session_maker)
                user_row = await get_user(event.from_user.id, session_maker)
                await event.bot.send_message(chat_id=int(conf.admin_topic),
                                             message_thread_id=int(user_row.topic_id),
                                             text=f'<b>🔔 Пользователь только что зарегистрировался!\n\n'
                                                  f'ID в ТГ: <code>{user_row.telegram_id}</code>\n'
                                                  f'Имя: <code>{user_row.telegram_fullname}</code>\n'
                                                  f'ID в БД: <code>{user_row.id}</code>\n'
                                                  f'Верификация номера телефона: <code>False ❌</code></b>',
                                             reply_markup=await admin_topic_kb())
                return await handler(event, data)
            else:
                return await handler(event, data)
