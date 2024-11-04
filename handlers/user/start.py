import logging

from aiogram import types, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.user import get_user, get_user_dict
from keyboards.admin.admin_keyboard import admin_topic_kb
from keyboards.user.user_keyboard import get_phone_kb, menu_kb
from src.config import conf
from utils.states.user import FSMStart
from utils.texts import incoming_text


async def start_command(message: types.Message, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    if message.message_thread_id is not None:
        user_info = await get_user_dict({'topic_id': message.message_thread_id}, session_maker)
        await bot.send_message(chat_id=int(conf.admin_topic),
                               message_thread_id=int(message.message_thread_id),
                               text=f'<b>ФИО: <code>{user_info.user_fio}</code>\n'
                                    f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                    f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                                    f'ID в БД: <code>{user_info.id}</code>\n'
                                    f'️Верификация номера телефона: <code>True ✅</code></b>',
                               reply_markup=await admin_topic_kb())
    else:
        user_info = await get_user(message.from_user.id, session_maker)
        if user_info.verify is False:
            try:
                await data['msg'].delete()
            except (TelegramBadRequest,KeyError):
                pass
            await message.delete()
            await state.set_state(FSMStart.start_registration)

            msg = await message.answer(
                '<b>Для начала нашей совместной работы тебе нужно указать номер телефона с помощью кнопки  📱\n\n'
                'Либо напишите вручную ваш номер который вы указывали при оплате📱\n'
                '❗️<i>Формат номера</i> <code>+7XXXXXXXXXX</code>\n\n'
                'А так же, согласиться с правилами нашего сообщества 👇</b>\n\n'
                '<a href="https://www.youtube.com/watch?v=dQw4w9WgXcQ">Ссылка</a>',
                reply_markup=await get_phone_kb(),
                disable_web_page_preview=True)
        else:
            try:
                try:
                    await message.delete()
                except (TelegramBadRequest, KeyError):
                    pass
                msg = await data['msg'].edit_text(
                    text=incoming_text,
                    reply_markup=await menu_kb(session_maker, message.from_user.id))
            except (TelegramBadRequest, KeyError) as _ex:
                logging.error(_ex)
                try:
                    await message.delete()
                except (TelegramBadRequest, KeyError):
                    pass
                msg = await message.answer(
                    text=incoming_text,
                    reply_markup=await menu_kb(session_maker, message.from_user.id))
        await state.update_data(msg=msg)


async def main_menu(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    user_info = await get_user(call.from_user.id, session_maker)
    data = await state.get_data()
    if user_info.verify is True:
        try:
            msg = await data['msg'].edit_text(
                text=incoming_text,
                reply_markup=await menu_kb(session_maker, call.from_user.id))
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(
                text=incoming_text,
                reply_markup=await menu_kb(session_maker, call.from_user.id))
    else:
        await state.set_state(FSMStart.start_registration)

        try:
            msg = await data['msg'].edit_text(
                text=f'<b>Вы не указали ваш номер телефона 📱\n\n'
                     f'А так же предлагаем ещё раз ознакомиться с нашими правилами 👇</b>\n\n'
                     '<a href="https://www.youtube.com/watch?v=dQw4w9WgXcQ">Ссылка</a>',
                reply_markup=await get_phone_kb(),
                disable_web_page_preview=True)
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(
                text=f'<b>Вы не указали ваш номер телефона 📱\n\n'
                     f'А так же предлагаем ещё раз ознакомиться с нашими правилами 👇</b>\n\n'
                     '<a href="https://www.youtube.com/watch?v=dQw4w9WgXcQ">Ссылка</a>',
                reply_markup=await get_phone_kb(),
                disable_web_page_preview=True)
    await state.update_data(msg=msg)


def register_start_handler(dp: Dispatcher):
    dp.message.register(start_command, Command('start'))
    dp.callback_query.register(main_menu, F.data == 'main_menu')
