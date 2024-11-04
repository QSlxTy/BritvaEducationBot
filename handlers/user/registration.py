import asyncio
import logging

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.new_user import is_phone_exists, get_new_user, update_new_user
from integrations.database.models.user import update_user, get_user
from keyboards.admin.admin_keyboard import admin_topic_kb
from keyboards.user.user_keyboard import to_menu_kb
from src.config import conf
from utils.SMS import send_sms
from utils.states.admin import FSMReg
from utils.states.user import FSMPhone, FSMStart


async def get_phone_number(message: types.Message, session_maker: sessionmaker, state: FSMContext):
    data = await state.get_data()
    await message.delete()
    await data['msg'].delete()
    await state.set_state(FSMPhone.get_phone_number)
    if message.contact:
        phone = '8' + message.contact.phone_number[2:]
    else:
        phone = '8' + message.text[2:]
    if not await is_phone_exists(phone, session_maker):
        msg = await message.answer(
            text='<b>К сожалению, вы не оплатили подписку на наш сервис, '
                 'сделать вы это сможете на нашем официальном сайте\n\n'
                 '❗️После оплаты, начните процесс регистрации 👉 /start</b>'
        )
        await state.update_data(msg=msg)
        return
    use_info = await get_new_user(phone, session_maker)
    if use_info.verify_access is True:
        msg = await message.answer(
            text='<b>К сожалению такой аккаунт уже есть\n'
                 '/start</b>'
        )
        await state.update_data(msg=msg)
        return
    json = await send_sms(phone)
    await update_user(message.from_user.id, {'phone': str(phone)}, session_maker)
    msg = await message.answer(
        text='<b>Вам нужно подвердить владение телефоном. 📲\n\n'
             'Сейчас на ваш номер поступит звонок. Пожалуйста, '
             'укажите <code>код</code> который вам скажет автоответчик\n\n'
             'Ваш номер в надёжном месте 🛡</b>'
    )
    await state.update_data(msg=msg, code=json['data']['pincode'], phone=phone)
    data = await state.get_data()
    await asyncio.sleep(60)
    user_info = await get_user(message.from_user.id, session_maker)
    if user_info.verify == 0:
        try:
            msg = await data['msg'].edit_text(
                text='<b>Не пришёл звонок?, попробуйте пройти регистрацию заново\n\n</b>'
                     '<i>*️Для этого нажмите /start ❗️</i>'
            )
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            msg = await message.answer(
                text='<b>Не пришёл звонок?, попробуйте пройти регистрацию заново\n\n</b>'
                     '<i>*️Для этого нажмите /start ❗️</i>'
            )
        await state.update_data(msg=msg)
    else:
        pass


async def verify_phone(message: types.Message, session_maker: sessionmaker, state: FSMContext):
    await state.set_state(FSMPhone.get_phone_number)
    data = await state.get_data()
    await update_new_user(data['phone'], {'verify_access': True}, session_maker)

    await message.delete()
    if int(data['code']) == int(message.text):
        try:
            await state.set_state(FSMReg.verify_phone)
            msg = await data['msg'].edit_text(
                '<b>✅ Регистрация прошла успешно\n\n'
                'Остался последний этап...\n\n'
                'Укажите свои данные в формате \n'
                '<code>Фамилия Имя </code>\n\n'
                'Данные будут использоватся для занесения в сертификат при его получении</b>\n\n'
                '*️<i>Перед отправкой тщательно проверьте, данные изменить будет нельзя ❗️</i>'
            )
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await message.delete()
            msg = await message.answer(
                '<b>✅ Регистрация прошла успешно\n\n'
                'Остался последний этап...\n\n'
                'Укажите свои данные ФИО в формате \n'
                'Фамилия Имя Отчество\n\n'
                'Данные будут использоватся для занесения в сертификат при его получении</b>\n\n'
                '*️<i>Перед отправкой тщательно проверьте, данные изменить будет нельзя ❗️</i>'
            )
        user_info = await get_user(message.from_user.id, session_maker)
        await bot.send_message(chat_id=int(conf.admin_topic),
                               message_thread_id=int(user_info.topic_id),
                               text=f'<b>🔔 Пользователь подтвердил номер телефона\n\n'
                                    f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                    f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                                    f'ID в БД: <code>{user_info.id}</code>\n'
                                    f'⭐️ Верификация номера телефона: <code>True ✅</code></b>',
                               reply_markup=await admin_topic_kb())
        await update_user(message.from_user.id, {'verify': True}, session_maker)
    else:
        try:
            msg = await data['msg'].edit_text('<b>❌ Вы указали неверный код\n'
                                              'Вы можете ввести код ещё раз или начать операцию заново</b>\n\n'
                                              '<i>*️Для этого нажмите /start ❗️</i>')
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await message.delete()
            msg = await message.answer('<b>❌ Вы указали неверный код\n'
                                       'Вы можете ввести код ещё раз или начать операцию заново</b>\n\n'
                                       '<i>*️Для этого нажмите /start ❗️</i>')
    await state.update_data(msg=msg)


async def get_fio(message: types.Message, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    await message.delete()
    await update_user(message.from_user.id, {'user_fio': message.text}, session_maker)
    try:
        await state.set_state(FSMReg.verify_phone)
        msg = await data['msg'].edit_text(
            '<b>Регистрация завершена ✔️</b>',
            reply_markup=await to_menu_kb()
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await message.delete()
        msg = await message.answer(
            '<b>Регистрация завершена ✔️</b>',
            reply_markup=await to_menu_kb()
        )
    user_info = await get_user(message.from_user.id, session_maker)
    await bot.send_message(chat_id=int(conf.admin_topic),
                           message_thread_id=int(user_info.topic_id),
                           text=f'<b>🔔 Пользователь указал ФИО\n\n'
                                f'⭐ ФИО: <code>{user_info.user_fio}</code>\n'
                                f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                                f'ID в БД: <code>{user_info.id}</code>\n'
                                f'️Верификация номера телефона: <code>True ✅</code></b>',
                           reply_markup=await admin_topic_kb())
    await state.clear()
    await state.update_data(msg=msg)


def register_handler(dp: Dispatcher):
    dp.message.register(get_phone_number, FSMStart.start_registration, F.content_type.in_({'contact', 'text'}))
    dp.message.register(verify_phone, F.content_type == 'text', FSMPhone.get_phone_number)
    dp.message.register(get_fio, F.content_type == 'text', FSMReg.verify_phone)
