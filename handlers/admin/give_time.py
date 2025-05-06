import logging
from datetime import timedelta, datetime

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.policy_status import update_learning_status, get_learning_status
from integrations.database.models.user import get_user_dict
from keyboards.admin.admin_keyboard import choose_give_time_kb, admin_topic_kb, delete_message_kb
from utils.states.admin import FSMTopic


async def choose_give_time(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    user_info = await get_user_dict({'topic_id': call.message.message_thread_id}, session_maker)

    if 'yes' in call.data:
        try:
            msg = await data['msg'].edit_text(
                text=f'<b>🔔 Вы успешно выдали пользователю дополнительное время\n\n'
                     f'ФИО: <code>{user_info.user_fio}</code>\n'
                     f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                     f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                     f'ID в БД: <code>{user_info.id}</code>\n'
                     f'Верификация номера телефона: <code>True ✅</code></b>',
                reply_markup=await admin_topic_kb()
            )
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(
                text=f'<b>🔔 Вы успешно выдали пользователю дополнительное время\n\n'
                     f'ФИО: <code>{user_info.user_fio}</code>\n'
                     f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                     f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                     f'ID в БД: <code>{user_info.id}</code>\n'
                     f'Верификация номера телефона: <code>True ✅</code></b>',
                reply_markup=await admin_topic_kb()
            )
        policy_info = await get_learning_status(user_info.telegram_id, session_maker)
        if policy_info.date_start + timedelta(days=3) < datetime.now():
            await update_learning_status(user_info.telegram_id,
                                         {'date_start': datetime.now() + timedelta(hours=int(data['time']))},
                                         session_maker)
        else:
            await update_learning_status(user_info.telegram_id,
                                         {'date_start': policy_info.date_start + timedelta(hours=int(data['time']))},
                                         session_maker)
        await bot.send_message(
            chat_id=policy_info.telegram_id,
            text='<b>Вам было выдано дополнительное время ✅</b>',
            reply_markup=await delete_message_kb()
        )
    else:
        try:
            msg = await data['msg'].edit_text(
                text=f'<b>Вы отменили процесс выдачи дополнительного времени ⭕️</b>',
                reply_markup=await admin_topic_kb()
            )
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(
                text=f'<b>Вы отменили процесс выадчи дополнительного врмени ⭕️</b>',
                reply_markup=await admin_topic_kb()
            )
    await state.update_data(msg=msg)


async def give_time(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(FSMTopic.give_time)
    msg = await call.message.answer(
        text=f'<b>Укажите количество дополнительных часов</b>'
    )
    await state.update_data(msg=msg)


async def get_time_msg(message: types.Message, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    time = message.text
    await message.delete()
    user_info = await get_user_dict({'topic_id': message.message_thread_id}, session_maker)
    try:
        msg = await data['msg'].edit_text(
            text=f'<b>Вы точно хотите продлить доступ к курсу пользователю...\n\n'
                 f'ФИО: <code>{user_info.user_fio}</code>\n'
                 f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                 f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                 f'... на <code>{time}</code> часов</b>',
            reply_markup=await choose_give_time_kb()
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        msg = await message.answer(
            text=f'<b>Вы точно хотите продлить доступ к курсу пользователю...\n\n'
                 f'ФИО: <code>{user_info.user_fio}</code>\n'
                 f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                 f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                 f'... на <code>{time}</code> часов</b>',
            reply_markup=await choose_give_time_kb()
        )

    await state.update_data(msg=msg, time=time)


def register_handler(dp: Dispatcher):
    dp.callback_query.register(give_time, F.data == 'give_time')
    dp.callback_query.register(choose_give_time, F.data.startswith('time'))
    dp.message.register(get_time_msg, FSMTopic.give_time, F.content_type == 'text')
