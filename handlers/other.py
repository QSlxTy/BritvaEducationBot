from aiogram import Dispatcher, types, F
from aiogram.exceptions import TelegramAPIError


async def delete_message(call: types.CallbackQuery):
    try:
        await call.message.delete()
    except TelegramAPIError:
        ...


def register_other_handlers(dp: Dispatcher):
    dp.callback_query.register(delete_message, F.data == 'message_delete')