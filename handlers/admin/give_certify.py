import logging

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.user import get_user_dict, update_user
from keyboards.admin.admin_keyboard import admin_topic_kb, choose_give_certify_kb
from keyboards.user.user_keyboard import back_menu_kb
from utils.generate_certify import generate_certify


async def choose_certify_user(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    user_info = await get_user_dict({'topic_id': call.message.message_thread_id}, session_maker)
    try:
        msg = await data['msg'].edit_text(text=f'<b>Вы точно хотите вручить сертификат пользователю...\n\n'
                                               f'ФИО: <code>{user_info.user_fio}</code>\n'
                                               f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                               f'Имя: <code>{user_info.telegram_fullname}</code>\n</b>',
                                          reply_markup=await choose_give_certify_kb())
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(text=f'<b>Вы точно хотите вручить сертификат пользователю...\n\n'
                                             f'ФИО: <code>{user_info.user_fio}</code>\n'
                                             f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                             f'Имя: <code>{user_info.telegram_fullname}</code>\n</b>',
                                        reply_markup=await choose_give_certify_kb())

    await state.update_data(msg=msg)


async def give_certify(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    user_info = await get_user_dict({'topic_id': call.message.message_thread_id}, session_maker)
    if 'yes' in call.data:
        try:
            msg = await data['msg'].edit_text(text=f'<b>Пользователю...</b>\n\n'
                                                   f'ФИО: <code>{user_info.user_fio}</code>\n'
                                                   f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                                   f'Имя: <code>{user_info.telegram_fullname}</code>\n\n'
                                                   f'...Был выдан сертификат ✅</b>',
                                              reply_markup=await admin_topic_kb())
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(text=f'<b>Пользователю...\n\n'
                                                 f'ФИО: <code>{user_info.user_fio}</code>\n'
                                                 f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                                 f'Имя: <code>{user_info.telegram_fullname}</code>\n\n'
                                                 f'...Был выдан сертификат ✅</b>',
                                            reply_markup=await admin_topic_kb())
        await update_user(user_info.telegram_id, {'access': False}, session_maker)
        url = await generate_certify(user_info.telegram_fullname, user_info.telegram_id)
        await bot.send_photo(chat_id=user_info.telegram_id,
                             photo=url,
                             caption='<b>Вам был выдан сертификат ✅\n\n'
                                     'Поздравляем</b>',
                             reply_markup=await back_menu_kb())
    else:
        try:
            msg = await data['msg'].edit_text(f'<b>Вы отменили процесс выдачи сертификата ⭕️</b>',
                                              reply_markup=await admin_topic_kb())
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(f'<b>Вы отменили процесс выдачи сертификата ⭕️</b>',
                                            reply_markup=await admin_topic_kb())
    await state.update_data(msg=msg)


def register_handler(dp: Dispatcher):
    dp.callback_query.register(choose_certify_user, F.data == 'give_certify')
    dp.callback_query.register(give_certify, F.data.startswith('certify'))
