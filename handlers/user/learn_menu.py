import logging
from datetime import datetime

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.lessons import get_lessons
from integrations.database.models.policy_status import get_learning_status, update_learning_status
from integrations.database.models.user import get_user
from keyboards.admin.admin_keyboard import admin_topic_kb
from keyboards.user.user_keyboard import menu_learn_kb, back_menu_kb
from src.config import conf
from utils.aiogram_helper import generate_progress_bar


async def learn_info(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    policy_info = await get_learning_status(call.from_user.id, session_maker)
    user_info = await get_user(call.from_user.id, session_maker)
    if policy_info.status == 'Не начинал':
        await update_learning_status(call.from_user.id, {'status': 'Начал'}, session_maker)
        if policy_info.policy == 'barber':
            text = 'Мастер ✂️'
        else:
            text = 'Администратор 🤵'
        await bot.send_message(chat_id=int(conf.admin_topic),
                               message_thread_id=int(user_info.topic_id),
                               text=f'<b>🔔 Пользователь начал обучение</b>\n\n'
                                    f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                    f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                                    f'Юзернейм в ТГ: <code>{user_info.telegram_username}</code>\n'
                                    f'ID в БД: <code>{user_info.id}</code>\n'
                                    f'Направление <code>{text}</code>\n'
                                    f'⭐️ Начало обучения {datetime.now()}\n'
                                    f'Верификация номера телефона: <code>True ✅</code>',
                               reply_markup=await admin_topic_kb())
    policy_info = await get_learning_status(call.from_user.id, session_maker)
    max_score = await get_lessons(policy_info.policy, session_maker)
    progress_bar = await generate_progress_bar(policy_info.last_lesson_id, len(max_score))
    if policy_info.count_try <= 0:
        try:
            msg = await data['msg'].edit_text(
                text=f'<b>К сожалению у вас закончились попытки для прохождения обучения</b>',
                reply_markup=await back_menu_kb())
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(
                text=f'<b>К сожалению у вас закончились попытки для прохождения обучения</b>',
                reply_markup=await back_menu_kb())
        await state.update_data(msg=msg)
    else:
        try:
            msg = await data['msg'].edit_text(f'<b>Ваша статистика прохождения обучения\n\n'
                                              f'{progress_bar}</b>\n\n'
                                              f'<i>*️Нажмите кнопку для начала или продолжения обучения❗️</i>',
                                              reply_markup=await menu_learn_kb())
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(f'<b>Ваша статистика прохождения обучения\n\n'
                                            f'{progress_bar}</b>\n\n'
                                            f'<i>*️Нажмите кнопку для начала или продолжения обучения❗️</i>',
                                            reply_markup=await menu_learn_kb())
    await state.update_data(msg=msg)


def register_handler(dp: Dispatcher):
    dp.callback_query.register(learn_info, F.data == 'learning_info')
