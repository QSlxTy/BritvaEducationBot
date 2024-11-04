import logging
from datetime import datetime

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.user import get_user_dict, update_user
from keyboards.admin.admin_keyboard import choose_add_user_kb, delete_message_kb
from keyboards.user.user_keyboard import back_menu_kb
from utils.states.admin import FSMAddUser


async def choose_add_user(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(FSMAddUser.add_user)
    data = await state.get_data()
    try:
        msg = await data['msg'].edit_text(
            text=
            f'<b>Чтобы открыть пользователю доступ к курсу, вам нужно указать его <code>@username</code>\n\n'
            f'Важно❗️ Перед этим, пользователь должен нажать /start для того, чтобы бот его узнал</b>',
            reply_markup=await back_menu_kb()
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(
            text=
            f'<b>Чтобы открыть пользователю доступ к курсу, вам нужно указать его <code>@username</code>\n'
            f'Важно❗️ Перед этим, пользователь должен нажать /start для того, чтобы бот его узнал</b>',
            reply_markup=await back_menu_kb()
        )
    await state.update_data(msg=msg)


async def add_user(message: types.Message, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    username = message.text.replace('@', '')
    user_info = await get_user_dict({'telegram_username': username}, session_maker)
    await message.delete()
    try:
        msg = await data['msg'].edit_text(f'<b>Открыть пользователю...\n\n'
                                          f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                          f'Username: <code>{user_info.telegram_username}</code>\n'
                                          f'Имя: <code>{user_info.telegram_fullname}</code>\n\n'
                                          f'...доступ к курсу?</b>',
                                          reply_markup=await choose_add_user_kb())
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await message.delete()
        msg = await message.answer(f'<b>Открыть пользователю...'
                                   f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                   f'Username: <code>{user_info.telegram_username}</code>\n'
                                   f'Имя: <code>{user_info.telegram_fullname}</code>\n\n'
                                   f'...доступ к курсу?</b>',
                                   reply_markup=await choose_add_user_kb())
    await state.update_data(msg=msg, user_add_id=user_info.telegram_id)


async def choose_add(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    if 'yes' in call.data:
        try:
            msg = await data['msg'].edit_text(
                text=
                f'<b>Пользователю был выдан доступ к курсу на 72 часа</b>',
                reply_markup=await back_menu_kb()
            )
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(
                text=
                f'<b>Пользователю был выдан доступ к курсу на 72 часа</b>',
                reply_markup=await back_menu_kb()
            )
        await update_user(data['user_add_id'], {'access': True,
                                                'verify': True,
                                                'date_registration': datetime.now()}, session_maker)
        await bot.send_message(chat_id=data['user_add_id'],
                               text=f'<b>⚙️ Администратор выдал вам доступ к курсу</b>',
                               reply_markup=await delete_message_kb())
    else:
        try:
            msg = await data['msg'].edit_text(
                text=
                f'<b>Вы отменили процесс выдачи пользователю доступа, нажмите /start</b>',
                reply_markup=await back_menu_kb()
            )
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(
                text=
                f'<b>Вы отменили процесс выдачи пользователю доступа, нажмите /start</b>',
                reply_markup=await back_menu_kb()
            )
    await state.update_data(msg=msg)


def register_handler(dp: Dispatcher):
    dp.callback_query.register(choose_add_user, F.data == 'add_user')
    dp.message.register(add_user, FSMAddUser.add_user, F.content_type == 'text')
    dp.callback_query.register(choose_add, F.data.startswith('user_add'))
