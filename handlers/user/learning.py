import logging
import os

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.lessons import get_lessons
from integrations.database.models.new_user import delete_newreg
from integrations.database.models.policy_status import get_learning_status, update_learning_status, delete_policy
from integrations.database.models.qestions import get_questions_by_media, get_count_questions
from integrations.database.models.user import get_user, delete_user_db
from integrations.database.sql_alch import create_connection, get_session_maker, init_models
from keyboards.admin.admin_keyboard import admin_topic_kb
from keyboards.user.user_keyboard import select_page_kb, back_menu_kb, answers_kb
from src.config import conf
from utils.aiogram_helper import generate_progress_bar
from utils.generate_certify import generate_certify


async def learning_process(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    user_info = await get_learning_status(call.from_user.id, session_maker)
    lessons_list = await get_lessons(user_info.policy, session_maker)
    data = await state.get_data()
    if user_info.count_try <= 0:
        try:
            msg = await data['msg'].edit_text(
                text=f'<b>К сожалению у вас закончились попытки для прохождения обучения\n\n'
                     f'Оплатите курс ещё раз и нажмите старт</b>'
                     f'/start')
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(
                text=f'<b>К сожалению у вас закончились попытки для прохождения обучения\n\n'
                     f'Оплатите курс ещё раз и нажмите старт</b>'
                     f'/start')
        user_info = await get_user(call.from_user.id, session_maker)
        await delete_user_db(user_info.telegram_id, session_maker)
        await delete_policy(user_info.telegram_id, session_maker)
        await delete_newreg(user_info.phone, session_maker)
        await state.update_data(msg=msg)
    else:
        if user_info.status == ' Готово':
            try:
                msg = await data['msg'].edit_text(
                    text=f'<b>Вы уже прошли обучение, ожидайте получения сертификата ⏳</b>',
                    reply_markup=await back_menu_kb())
            except (TelegramBadRequest, KeyError) as _ex:
                logging.error(_ex)
                await call.message.delete()
                msg = await call.message.answer(text=f'<b>Вы уже прошли обучение, ожидайте получения сертификата ⏳</b>',
                                                reply_markup=await back_menu_kb())
            await state.update_data(msg=msg)
        else:
            await state.update_data(lessons=lessons_list, current_lesson=0, user_id=call.from_user.id)
            await send_lesson(call.from_user.id, state)


async def send_lesson(chat_id: int, state: FSMContext):
    data = await state.get_data()
    try:
        await data['msg'].delete()
    except (TelegramBadRequest, KeyError):
        pass
    connection = await create_connection()
    await init_models(connection)
    session_maker = get_session_maker(connection)
    try:
        data['count_test']
    except KeyError:
        await state.update_data(count_test=int(0))
    policy_info = await get_learning_status(data['user_id'], session_maker)
    msg_wait = await bot.send_message(text='<b>Файл слишком большой, отправляю, ожидайте ⏳\n'
                                           'Это займет <code>1-2</code> минуты</b>',
                                      chat_id=data['user_id'])
    try:
        if 'mp4' in data['lessons'][policy_info.last_lesson_id].path:
            msg = await bot.send_video(chat_id=data['user_id'],
                                       video=FSInputFile(data['lessons'][policy_info.last_lesson_id].path),
                                       caption=f'<b>{data["lessons"][policy_info.last_lesson_id].text}\n\n'
                                               f'Если ты ознакомился с материалом, пройди тестирование 👇</b>',
                                       reply_markup=await select_page_kb(),
                                       request_timeout=300)
        else:
            msg = await bot.send_photo(chat_id=data['user_id'],
                                       photo=FSInputFile(data['lessons'][policy_info.last_lesson_id].path),
                                       caption=f'<b>{data["lessons"][policy_info.last_lesson_id].text}\n\n'
                                               f'Если ты ознакомился с материалом, пройди тестирование 👇</b>',
                                       reply_markup=await select_page_kb(),
                                       request_timeout=300)
        await state.update_data(text=data["lessons"][policy_info.last_lesson_id].text,
                                path=data['lessons'][policy_info.last_lesson_id].path)
        await msg_wait.delete()
    except IndexError:
        await msg_wait.delete()
        policy_info = await get_learning_status(data['user_id'], session_maker)
        user_info = await get_user(data['user_id'], session_maker)
        max_score = await get_count_questions(session_maker, policy_info.policy)
        progress_bar_testing = await generate_progress_bar(policy_info.user_score, max_score)
        if policy_info.user_score < 90:
            await update_learning_status(data['user_id'], {'status': 'Не начинал',
                                                           'count_try': policy_info.count_try - 1,
                                                           'last_lesson_id': 0,
                                                           'user_score': 0}, session_maker)
            msg = await bot.send_message(
                data['user_id'],
                f"<b>Поздравляем, вы прошли обучение 🏁\n\n"
                f"К сожалению, вы не набрали достаточное количество баллов ❌\n\n"
                f"Ваш результат <code>{policy_info.user_score}</code> / <code>{max_score}</code>\n\n"
                f"{progress_bar_testing}\n\n</b>"
                f"<i>*️У вас осталось <code>{policy_info.count_try - 1}</code> попыток ❗️</i>\n"
                f"<i>*️️Если у вас остались попытки, пройдите обучение заново в меню /start ❗️</i>")
            await bot.send_message(
                chat_id=int(conf.admin_topic),
                message_thread_id=int(user_info.topic_id),
                text="<b>🔔 Пользователь НЕ прошёл тестирование ❌</b>\n\n"
                     f'ФИО: <code>{user_info.user_fio}</code>\n'
                     f'<b>ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                     f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                     f'ID в БД: <code>{user_info.topic_id}</code>\n'
                     f'Верификация номера телефона: <code>True ✅</code>\n\n'
                     f'⭐ Результат тестирования: <code>{policy_info.user_score}'
                     f'</code> / <code>{max_score}</code> баллов\n\n'
                     f'⭐ {progress_bar_testing}</b>',
                reply_markup=await admin_topic_kb())
        else:

            await update_learning_status(data['user_id'], {'status': 'Готово',
                                                           'count_try': policy_info.count_try - 1}, session_maker)
            msg = await bot.send_message(
                data['user_id'],
                f"<b>Поздравляем, вы прошли обучение 🏁\n\n"
                f"Ваш результат <code>{policy_info.user_score}</code> / <code>{max_score}</code>\n\n"
                f"{progress_bar_testing}</b>")
            file_path = await generate_certify(user_info.user_fio, user_info.telegram_id)

            await bot.send_photo(
                photo=FSInputFile(file_path),
                chat_id=int(conf.admin_topic),
                message_thread_id=int(user_info.topic_id),
                caption="<b>🔔 Пользователь прошёл тестирование ✅</b>\n\n"
                        f'ФИО: <code>{user_info.user_fio}</code>\n'
                        f'<b>ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                        f'Имя: <code>{user_info.telegram_fullname}</code>\n'
                        f'ID в БД: <code>{user_info.topic_id}</code>\n'
                        f'Верификация номера телефона: <code>True ✅</code>\n\n'
                        f'⭐ Результат тестирования: <code>{policy_info.user_score}'
                        f'</code> / <code>{max_score}</code> баллов\n\n'
                        f'⭐ {progress_bar_testing}</b>',
                reply_markup=await admin_topic_kb())
            await bot.send_photo(chat_id=user_info.telegram_id,
                                 photo=FSInputFile(file_path),
                                 caption='<b>Вам был выдан сертификат BRITVA ✅\n\n'
                                         'Поздравляем 🌟</b>')
            os.remove(file_path)
            await delete_user_db(user_info.telegram_id, session_maker)
            await delete_policy(user_info.telegram_id, session_maker)
            await delete_newreg(user_info.phone, session_maker)
    await state.update_data(msg=msg)


async def send_test(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    lessons_list = await get_questions_by_media(data['path'], session_maker)
    user_policy_info = await get_learning_status(data['user_id'], session_maker)

    await data['msg'].delete()
    try:
        formatted_message = '\n'.join(f"<code>{i + 1}.</code> {item}" for i, item in
                                      enumerate(lessons_list[data["count_test"]].
                                                answers.replace('🌟', '').replace('\n', '').split(';')))
        msg = await bot.send_message(chat_id=data['user_id'],
                                     text=f'{lessons_list[data["count_test"]].question}\n\n'
                                          f'<b>Варианты ответов:</b>\n\n'
                                          f'{formatted_message}',
                                     reply_markup=await answers_kb(lessons_list[data["count_test"]]))
        await state.update_data(msg=msg, question=lessons_list[data["count_test"]].question,
                                true_answer=lessons_list[data["count_test"]].true_answer)
    except IndexError:
        await update_learning_status(data['user_id'],
                                     {'last_lesson_id': user_policy_info.last_lesson_id + 1}, session_maker)
        await state.update_data(current_lesson=data['current_lesson'] + 1, user_id=call.from_user.id, count_test=0)
        await send_lesson(call.from_user.id, state)


async def test_handle(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    user_policy_info = await get_learning_status(data['user_id'], session_maker)
    lessons_list = await get_questions_by_media(data['path'], session_maker)
    true_answer = lessons_list[data["count_test"]].answers.replace('🌟', '').replace('\n', '').split(';')[
        data["true_answer"] - 1]
    user_answer = lessons_list[data["count_test"]].answers.replace('🌟', '').replace('\n', '').split(';')[
        int(call.data.split(":")[3]) - 1]
    try:
        user_info = await get_user(data['user_id'], session_maker)
        if 'True' in call.data:
            await call.answer('✅ Есть! Идем дальше')
            await bot.send_message(chat_id=int(conf.admin_topic),
                                   message_thread_id=int(user_info.topic_id),
                                   text=f'<b>Пользователь верно ответил на вопрос ✅\n\n'
                                        f'Вопрос: {data["question"]}\n\n'
                                        f'Правильный ответ: <code>{true_answer}</code>\n'
                                        f'Ответ: <code>{user_answer}</code></b>')
            await update_learning_status(data['user_id'], {'status': 'В процессе',
                                                           'user_score': user_policy_info.user_score + 1},
                                         session_maker)
        else:
            await call.answer('❌ Ух... ошибка')
            await bot.send_message(chat_id=int(conf.admin_topic),
                                   message_thread_id=int(user_info.topic_id),
                                   text=f'<b>Пользователь НЕ верно ответил на вопрос ❌\n\n'
                                        f'Вопрос: {data["question"]}\n\n'
                                        f'Правильный ответ: <code>{true_answer}</code>\n'
                                        f'Ответ: <code>{user_answer}</code></b>')
            await update_learning_status(data['user_id'], {'status': 'В процессе'},
                                         session_maker)
        await state.update_data(count_test=data['count_test'] + 1)
        await send_test(call, state, session_maker)
    except NoResultFound as _ex:
        await update_learning_status(data['user_id'],
                                     {'last_lesson_id': user_policy_info.last_lesson_id + 1}, session_maker)
        await state.update_data(current_lesson=data['current_lesson'] + 1, user_id=call.from_user.id, count_test=0)
        await send_lesson(call.from_user.id, state)


def register_handler(dp: Dispatcher):
    dp.callback_query.register(send_test, F.data == 'send_test')

    dp.callback_query.register(learning_process, F.data.startswith('start_learning')& ~F.data.equals('send_test'))
    dp.callback_query.register(test_handle, F.data.startswith('test_answer'))
