import logging
from datetime import datetime, timedelta

from aiogram import types, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.user import is_user_exists_by_username, update_user, get_user_by_username
from keyboards.admin.admin_keyboard import choose_add_admin_kb
from keyboards.user.user_keyboard import back_menu_kb
from src.config import Configuration
from utils.states.admin import FSMAddAdmin


async def add_admin(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    await state.set_state(FSMAddAdmin.add_admin)
    data = await state.get_data()
    try:
        msg = await data['msg'].edit_text(
            text=f'<b>Чтобы добавить администратора, вам нужно указать его <code>@username</code>\n\n'
                 f'Важно❗️ Перед этим, пользователь должен нажать /start для того, чтобы бот его узнал</b>',
            reply_markup=await back_menu_kb()
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(
            text=f'<b>Чтобы добавить администратора, вам нужно указать его <code>@username</code>\n\n'
                 f'Важно❗️ Перед этим, пользователь должен нажать /start для того, чтобы бот его узнал</b>',
            reply_markup=await back_menu_kb())
    await state.update_data(msg=msg)


async def get_admin(message: types.Message, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    name = message.text.replace('@', '')
    await state.update_data(new_admin=message.text.replace('@', ''))
    await message.delete()
    if await is_user_exists_by_username(name, session_maker):
        try:
            msg = await data['msg'].edit_text(
                text=f'<b>Вы хотите сделать пользователя @{name} администратором?</b>',
                reply_markup=await choose_add_admin_kb()
            )
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await message.delete()
            msg = await message.answer(text=f'<b>Вы хотите сделать пользователя @{name} администратором?</b>',
                                       reply_markup=await choose_add_admin_kb())
    else:
        try:
            msg = await data['msg'].edit_text(
                text=f'<b>Не удалось найти такого пользователя, попробуйте ещё раз</b>',
                reply_markup=await back_menu_kb()
            )
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await message.delete()
            msg = await message.answer(text=f'<b>Не удалось найти такого пользователя, попробуйте ещё раз</b>',
                                       reply_markup=await back_menu_kb())
    await state.update_data(msg=msg)


async def accept_add_admin(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    user_info = await get_user_by_username(data['new_admin'], session_maker)
    await update_user(user_info.telegram_id, {'is_admin': True,
                                              'verify': True,
                                              'access': True,
                                              'date_registration': datetime.now() + timedelta(days=99999)},
                      session_maker)
    try:
        msg = await data['msg'].edit_text(
            text=f'<b>Пользовтаель теперь администратор ⚙️</b>',
            reply_markup=await back_menu_kb()
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(
            text=f'<b>Пользовтаель теперь администратор ⚙️</b>',
            reply_markup=await back_menu_kb()
        )
    await bot.send_message(chat_id=user_info.telegram_id,
                           text='Вы теперь администратор, ваша пригласительная ссылка\n\n'
                                f'{Configuration.admin_topic_url}',
                           disable_web_page_preview=True)
    await state.update_data(msg=msg)


def register_handler(dp: Dispatcher):
    dp.callback_query.register(add_admin, F.data == 'add_admin')
    dp.message.register(get_admin, FSMAddAdmin.add_admin, F.content_type == 'text')
    dp.callback_query.register(accept_add_admin, F.data == 'admin_add')
