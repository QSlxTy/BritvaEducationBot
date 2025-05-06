import logging

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.policy_status import learning_status
from integrations.database.models.user import get_user
from keyboards.admin.admin_keyboard import admin_topic_kb
from keyboards.user.user_keyboard import choose_policy_kb, back_menu_kb
from src.config import conf
from utils.states.user import FSMPhone


async def choose_policy(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    await state.set_state(FSMPhone.get_phone_number)
    data = await state.get_data()
    try:
        msg = await data['msg'].edit_text(text='<b>🎓 Выберите курс для обучения из предложенных ниже\n\n</b>',
                                          reply_markup=await choose_policy_kb(call.from_user.id, session_maker))
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(text='<b>🎓 Выберите курс для обучения из предложенных ниже\n\n</b>',
                                        reply_markup=await choose_policy_kb(call.from_user.id, session_maker))
    await state.update_data(msg=msg)


async def get_policy(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    await state.set_state(FSMPhone.get_phone_number)
    data = await state.get_data()
    if call.data.split('_')[0] == 'admin':
        text = 'Администратор 🤵'
    else:
        text = 'Мастер ✂️'
    try:
        msg = await data['msg'].edit_text(text=f'<b>Вы выбрали курс: <code>{text}</code></b>',
                                          reply_markup=await back_menu_kb())
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(text=f'<b>Вы выбрали курс: <code>{text}</code></b>',
                                        reply_markup=await back_menu_kb())
    await state.update_data(msg=msg)
    await learning_status(call.from_user.id, call.data.split('_')[0], session_maker)
    user_info = await get_user(call.from_user.id, session_maker)
    await bot.send_message(chat_id=int(conf.admin_topic),
                           message_thread_id=int(user_info.topic_id),
                           text=f'<b>🔔 Пользователь выбрал направление\n\n'
                                f'ФИО: <code>{user_info.user_fio}</code>\n'
                                f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                                f'Юзернейм в ТГ: <code>{user_info.telegram_username}</code>\n'
                                f'ID в БД: <code>{user_info.id}</code>\n'
                                f'⭐️ Направление: <code>{text}</code>\n'
                                f'Верификация номера телефона: <code>True ✅</code></b>',
                           reply_markup=await admin_topic_kb())


def register_handler(dp: Dispatcher):
    dp.callback_query.register(choose_policy, F.data == 'choose_policy')
    dp.callback_query.register(get_policy, F.data.split('_')[1] == 'choose')
