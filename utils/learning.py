import logging
import os
import re

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from sqlalchemy.orm import sessionmaker

from bot_start import bot, logger
from integrations.database.models.lessons import get_lessons
from integrations.database.models.new_user import delete_newreg
from integrations.database.models.policy_status import get_learning_status, update_learning_status, delete_policy
from integrations.database.models.qestions import get_questions_by_media, get_count_questions, get_question_by_id
from integrations.database.models.user import get_user, delete_user_db
from keyboards.admin.admin_keyboard import admin_topic_kb
from keyboards.user.user_keyboard import select_page_kb, back_menu_kb, answers_kb
from src.config import conf
from utils.aiogram_helper import generate_progress_bar
from utils.generate_certify import generate_certify


async def learning_process(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    user_info = await get_learning_status(call.from_user.id, session_maker)
    lessons_list = await get_lessons(user_info.policy, session_maker)

    if user_info.count_try <= 0:
        await handle_no_attempts(call, user_info, state, session_maker)
    elif user_info.status == 'Готово':
        await handle_already_passed(call, state)
    else:
        await state.update_data(lessons=lessons_list, user_id=call.from_user.id)
        await send_lesson(session_maker, state)

    await state.update_data(user_id=call.from_user.id)


async def handle_no_attempts(call, user_info, state, session_maker):
    try:
        msg = await call.message.answer(
            text='<b>К сожалению у вас закончились попытки для прохождения обучения\n\n'
                 'Оплатите курс ещё раз и нажмите старт</b>/start'
        )
    except TelegramBadRequest as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(
            text='<b>К сожалению у вас закончились попытки для прохождения обучения\n\n'
                 'Оплатите курс ещё раз и нажмите старт</b>/start'
        )
    await delete_user_data(user_info, session_maker)
    await state.update_data(msg=msg)


async def delete_user_data(user_info, session_maker):
    await delete_user_db(user_info.telegram_id, session_maker)
    await delete_policy(user_info.telegram_id, session_maker)
    user_info = await get_user(user_info.telegram_id, session_maker)
    await delete_newreg(user_info.phone, session_maker)


async def handle_already_passed(call, state):
    try:
        msg = await call.message.answer(
            text='<b>Вы уже прошли обучение, ожидайте получения сертификата ⏳</b>',
            reply_markup=await back_menu_kb()
        )
    except TelegramBadRequest as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(
            text='<b>Вы уже прошли обучение, ожидайте получения сертификата ⏳</b>',
            reply_markup=await back_menu_kb()
        )
    await state.update_data(msg=msg)


async def send_lesson(session_maker, state: FSMContext):
    data = await state.get_data()
    await delete_previous_messages(data)
    try:
        data['count_test']
    except KeyError:
        await state.update_data(count_test=0)

    policy_info = await get_learning_status(user_id=int(data['user_id']), session_maker=session_maker)
    logger.error(f'send lesson. count lesson -- {policy_info.last_lesson_id} -- max {len(data["lessons"])}')

    # Проверка завершения курса
    if policy_info.last_lesson_id >= len(data["lessons"]):
        await handle_course_completion(data, policy_info, session_maker, state)
        return
    else:
        await send_current_lesson(data, policy_info, session_maker, state)


async def handle_course_completion(data, policy_info, session_maker, state):
    user_info = await get_user(data['user_id'], session_maker)
    max_score = await get_count_questions(session_maker, policy_info.policy)

    progress_bar_testing = await generate_progress_bar(policy_info.user_score, max_score)
    logger.info(f'End policy. score -- {policy_info.user_score} -- max score {max_score}')

    if policy_info.user_score < max_score * 0.9:
        await send_failure_message(data, user_info, max_score, progress_bar_testing, state, session_maker)
        await update_learning_status(data['user_id'], {
            'status': 'Не начинал',
            'count_try': policy_info.count_try - 1,
            'last_lesson_id': 0,
            'user_score': 0,
            'bad_answer_id': '0'
        }, session_maker)
        return
    else:
        await send_success_message(data, user_info, policy_info, max_score, progress_bar_testing, state, session_maker)
        await update_learning_status(data['user_id'], {
            'status': 'Готово',
            'count_try': policy_info.count_try - 1,
            'last_lesson_id': 0,
            'user_score': 0,
            'bad_answer_id': '0'
        }, session_maker)
        return


async def delete_previous_messages(data):
    for key in ['msg', 'msg_media', 'msg_list']:
        try:
            await data[key].delete()
        except Exception:
            pass


async def send_failure_message(data, user_info, max_score, progress_bar_testing, state, session_maker):
    policy_info = await get_learning_status(user_id=int(data['user_id']), session_maker=session_maker)
    msg = await bot.send_message(
        chat_id=data['user_id'],
        text=f"<b>К сожалению вы не прошли обучение\n\n"
             f"Вы не набрали достаточное количество баллов ❌\n\n"
             f"Ваш результат <code>{policy_info.user_score}</code> / <code>{max_score}</code>\n\n"
             f"{progress_bar_testing}\n\n</b>"
    )
    await send_bad_answers(data, policy_info, session_maker, state)
    await bot.send_message(
        chat_id=int(conf.admin_topic),
        message_thread_id=int(user_info.topic_id),
        text="<b>🔔 Пользователь НЕ прошёл тестирование ❌\n\n"
             f'ФИО: <code>{user_info.user_fio}</code>\n'
             f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
             f'Имя: <code>{user_info.telegram_fullname}</code>\n'
             f'ID в БД: <code>{user_info.topic_id}</code>\n'
             f'Верификация номера телефона: <code>True ✅</code>\n\n'
             f'⭐ Результат тестирования: <code>{policy_info.user_score}'
             f'</code> / <code>{max_score}</code> баллов\n\n'
             f'⭐ {progress_bar_testing}</b>',
        reply_markup=await admin_topic_kb()
    )

    await state.update_data(msg=msg)


async def send_success_message(data, user_info, policy_info, max_score, progress_bar_testing, state, session_maker):
    policy_info = await get_learning_status(user_id=int(data['user_id']), session_maker=session_maker)
    msg = await bot.send_message(
        chat_id=data['user_id'],
        text=f"<b>Поздравляем, вы прошли обучение 🏁\n\n"
             f"Ваш результат <code>{policy_info.user_score}</code> / <code>{max_score}</code>\n\n"
             f"{progress_bar_testing}\n\n</b>"
             f"<i>❗️ Сертификат удалится если вы нажмёте</i> /start"
    )
    await send_bad_answers(data, policy_info, session_maker, state)
    file_path = await generate_certify(user_info.user_fio, user_info.telegram_id, policy_info.policy)
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
                f'⭐ Результат тестирования: <code>{policy_info.user_score}</code> / <code>{max_score}</code> баллов\n\n'
                f'⭐ {progress_bar_testing}</b>',
        reply_markup=await admin_topic_kb()
    )
    await send_certification(user_info, file_path, state)

    await state.update_data(msg=msg)


async def send_certification(user_info, file_path, state):
    msg = await bot.send_photo(
        chat_id=user_info.telegram_id,
        photo=FSInputFile(file_path),
        caption='<b>Вам был выдан сертификат BRITVA ✅\n\n'
                'Поздравляем 🌟</b>'
    )
    os.remove(file_path)
    await state.update_data(msg_certify=msg)


async def send_bad_answers(data, policy_info, session_maker, state):
    logger.info(f'Send bad answers --> {policy_info.telegram_id}--> {policy_info.bad_answer_id}')
    msg_list = []
    str_questions = ''
    if len(policy_info.bad_answer_id.split(';')) > 0:
        for question_id in policy_info.bad_answer_id.split(';'):
            if int(question_id) == 0:
                pass
            else:
                question_info = await get_question_by_id(int(question_id), session_maker)
                str_questions += f"🔘 <code>{question_info.question}</code>\n"

        if len(str_questions) > 4000:
            questions = re.split(r'(🔘)', str_questions)
            parts = []
            current_part = "🔘"
            for i in range(1, len(questions), 2):
                question = questions[i]
                if len(current_part) + len(questions[i - 1]) > 4000:
                    parts.append(current_part)
                    current_part = "🔘" + question
                else:
                    current_part += "🔘" + question
            if current_part:
                parts.append(current_part)
            for part in parts:
                msg = await bot.send_message(
                    chat_id=data['user_id'],
                    text=f"<b>Вы допустили ошибки в следующих вопросах:</b>\n\n{part}\n"
                )
                msg_list.append(msg)
            msg = await bot.send_message(
                chat_id=data['user_id'],
                text="<i>Если у вас остались попытки, пройдите обучение заново в меню /start ❗️</i>"
            )
            msg_list.append(msg)
        else:
            msg = await bot.send_message(
                chat_id=data['user_id'],
                text=f"<b>Вы допустили ошибки в следующих вопросах:</b>\n\n"
                     f"{str_questions}\n"
                     f"<i>*️У вас осталось <code>{policy_info.count_try - 1}</code> попыток ❗️</i>\n"
                     f"<i>Если у вас остались попытки, пройдите обучение заново в меню /start ❗️</i>"
            )
            msg_list.append(msg)
    else:
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text=f"<i>*️У вас осталось <code>{policy_info.count_try - 1}</code> попыток ❗️</i>\n"
                 f"<i>Если у вас остались попытки, пройдите обучение заново в меню /start ❗️</i>"
        )
        msg_list.append(msg)
    await state.update_data(msg_list=msg_list)
    return


async def send_current_lesson(data, policy_info, session_maker, state):
    policy_info = await get_learning_status(user_id=int(data['user_id']), session_maker=session_maker)

    logger.info(f"Lesson --> {data['lessons'][policy_info.last_lesson_id].path.split(';')[0]}")
    list_sql = await get_questions_by_media(data['lessons'][policy_info.last_lesson_id].path.split(';')[0],
                                            session_maker)
    logger.info(f"Questions --> {list_sql}")
    logger.info(f'Count lesson --> {policy_info.last_lesson_id + 1} - {len(data["lessons"])}')

    text, text_kb = await determine_lesson_text_and_button(data, policy_info, list_sql)

    msg_wait = await bot.send_message(
        text='<b>Файл слишком большой, отправляю, ожидайте ⏳\n'
             'Это займет <code>1-2</code> минуты</b>',
        chat_id=data['user_id']
    )

    await send_media(data, policy_info, msg_wait, text, text_kb, state)


async def determine_lesson_text_and_button(data, policy_info, list_sql):
    if policy_info.last_lesson_id + 1 == len(data['lessons']):
        return 'Если ты ознакомился с материалом, заверши курс 👇', '✅ Завершить курс'
    elif not list_sql:
        return 'Если ты ознакомился с материалом, приступай к следующему уроку 👇', '📋 Следующий урок'
    else:
        return 'Если ты ознакомился с материалом, пройди тестирование 👇', '📋 Пройти тест'


async def send_media(data, policy_info, msg_wait, text, text_kb, state):
    media_path = data['lessons'][policy_info.last_lesson_id].path

    if len(media_path.split(';')) == 1:
        media_type = media_path.split(';')[0].split('.')[-1]
        if media_type in ['mp4', 'png', 'mp3']:
            await send_single_media(data, policy_info, media_path, media_type, text, text_kb, state)
        else:
            msg_media = await bot.send_message(
                chat_id=data['user_id'],
                text=f'<b>{data["lessons"][policy_info.last_lesson_id].text}\n\n</b>',
                disable_web_page_preview=True,
                reply_markup=await select_page_kb(text_kb)
            )
            await state.update_data(text=data["lessons"][policy_info.last_lesson_id].text,
                                    path=data['lessons'][policy_info.last_lesson_id].path,
                                    msg=msg_media)
        await msg_wait.delete()
    else:
        await send_more_media(data, policy_info, msg_wait, state)


async def send_more_media(data, policy_info, msg_wait, state):
    logger.info(f'Send more media --> {policy_info.telegram_id} --> '
                f'{data["lessons"][policy_info.last_lesson_id].path.split(";")[0]}')

    if 'состав_звонка' in data['lessons'][policy_info.last_lesson_id].path.split(';')[0]:
        msg_list = []
        msg = await bot.send_video(
            video=FSInputFile(data['lessons'][policy_info.last_lesson_id].path.split(';')[0]),
            chat_id=data['user_id'],
            caption=data['lessons'][policy_info.last_lesson_id].text.split(';')[0],
            width=1080,
            height=1920
        )
        await msg_wait.delete()
        msg_list.append(msg)
        for index, path in enumerate(data['lessons'][policy_info.last_lesson_id].path.split(';')):
            if 1 <= index <= 3:
                msg = await bot.send_audio(
                    chat_id=data['user_id'],
                    audio=FSInputFile(path)
                )
                msg_list.append(msg)
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Если ты ознакомился с материалом, перейди к следующему этапу 👇',
            reply_markup=await select_page_kb('📋 Сладующий этап')
        )
        msg_list.append(msg)
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[0])
    elif 'решение_ситуаций' in data['lessons'][policy_info.last_lesson_id].path.split(';')[0]:
        msg_list = []
        msg = await bot.send_video(
            video=FSInputFile(data['lessons'][policy_info.last_lesson_id].path.split(';')[0]),
            chat_id=data['user_id'],
            caption=data['lessons'][policy_info.last_lesson_id].text,
            width=1080,
            height=1920
        )
        msg_list.append(msg)
        await msg_wait.delete()
        for index, path in enumerate(data['lessons'][policy_info.last_lesson_id].path.split(';')):
            if 1 <= index <= 3:
                msg = await bot.send_audio(
                    chat_id=data['user_id'],
                    audio=FSInputFile(path)
                )
                msg_list.append(msg)
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Если ты ознакомился с материалом, пройди тестирование 👇',
            reply_markup=await select_page_kb('📋 Пройти тест')
        )
        msg_list.append(msg)
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[0])
    elif '/root/bot_britva/audio/AUDIO-2024-06-25-12-42-18.mp3' in data['lessons'][policy_info.last_lesson_id].path.split(';')[0]:
        msg_list = []
        await msg_wait.delete()
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Прослушай ещё 2 записи и укажи ошибки в тесте')
        msg_list.append(msg)
        for index, path in enumerate(data['lessons'][policy_info.last_lesson_id].path.split(';')):
            if 0 <= index <= 1:
                msg = await bot.send_audio(
                    chat_id=data['user_id'],
                    audio=FSInputFile(path)
                )
                msg_list.append(msg)
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Если ты ознакомился с материалом, пройди тестирование 👇',
            reply_markup=await select_page_kb('📋 Пройти тест')
        )
        msg_list.append(msg)
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[0])

    elif 'работа_лист_ожидания' in data['lessons'][policy_info.last_lesson_id].path.split(';')[0]:
        msg_list = []
        msg = await bot.send_video(
            video=FSInputFile(data['lessons'][policy_info.last_lesson_id].path.split(';')[0]),
            chat_id=data['user_id'],
            caption=data['lessons'][policy_info.last_lesson_id].text,
            width=1080,
            height=1920
        )
        msg_list.append(msg)
        await msg_wait.delete()
        for index, path in enumerate(data['lessons'][policy_info.last_lesson_id].path.split(';')):
            if 1 <= index <= 3:
                msg = await bot.send_audio(
                    chat_id=data['user_id'],
                    audio=FSInputFile(path)
                )
                msg_list.append(msg)
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Если ты ознакомился с материалом, пройди тестирование 👇',
            reply_markup=await select_page_kb('📋 Пройти тест')
        )
        msg_list.append(msg)
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[0])
    elif 'коммерческая_запись' in data['lessons'][policy_info.last_lesson_id].path.split(';')[0]:
        msg_list = []
        msg = await bot.send_video(
            video=FSInputFile(data['lessons'][policy_info.last_lesson_id].path.split(';')[0]),
            chat_id=data['user_id'],
            caption=data['lessons'][policy_info.last_lesson_id].text,
            width=1080,
            height=1920
        )
        msg_list.append(msg)
        await msg_wait.delete()
        for index, path in enumerate(data['lessons'][policy_info.last_lesson_id].path.split(';')):
            if 1 <= index <= 3:
                msg = await bot.send_audio(
                    chat_id=data['user_id'],
                    audio=FSInputFile(path)
                )
                msg_list.append(msg)
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Если ты ознакомился с материалом, пройди тестирование 👇',
            reply_markup=await select_page_kb('📋 Пройти тест')
        )
        msg_list.append(msg)
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[0])
    elif 'сколько_стрижка' in data['lessons'][policy_info.last_lesson_id].path.split(';')[0]:
        msg_list = []
        msg = await bot.send_video(
            video=FSInputFile(data['lessons'][policy_info.last_lesson_id].path.split(';')[0]),
            chat_id=data['user_id'],
            caption=data['lessons'][policy_info.last_lesson_id].text,
            width=1080,
            height=1920
        )
        msg_list.append(msg)
        await msg_wait.delete()
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[0])
        for index, path in enumerate(data['lessons'][policy_info.last_lesson_id].path.split(';')):
            if index == 1:
                msg = await bot.send_audio(
                    chat_id=data['user_id'],
                    audio=FSInputFile(path)
                )
                msg_list.append(msg)
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Если ты ознакомился с материалом, пройди тестирование 👇',
            reply_markup=await select_page_kb('📋 Пройти тест')
        )
        msg_list.append(msg)
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[0])
    elif 'ежедневный_обзвон' in data['lessons'][policy_info.last_lesson_id].path.split(';')[0]:
        msg_list = []
        msg = await bot.send_video(
            video=FSInputFile(data['lessons'][policy_info.last_lesson_id].path.split(';')[0]),
            chat_id=data['user_id'],
            caption=data['lessons'][policy_info.last_lesson_id].text,
            width=1080,
            height=1920
        )
        await msg_wait.delete()
        msg_list.append(msg)
        for index, path in enumerate(data['lessons'][policy_info.last_lesson_id].path.split(';')):
            if 1 <= index <= 3:
                msg = await bot.send_audio(
                    chat_id=data['user_id'],
                    audio=FSInputFile(path)
                )
                msg_list.append(msg)
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Если ты ознакомился с материалом, пройди тестирование 👇',
            reply_markup=await select_page_kb('📋 Пройти тест')
        )
        msg_list.append(msg)
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[0])
    elif 'кто_такой_топ' in data['lessons'][policy_info.last_lesson_id].path.split(';')[0]:
        msg_list = []
        msg = await bot.send_video(
            video=FSInputFile(data['lessons'][policy_info.last_lesson_id].path.split(';')[0]),
            chat_id=data['user_id'],
            caption=data['lessons'][policy_info.last_lesson_id].text,
            width=1080,
            height=1920
        )
        await msg_wait.delete()
        msg_list.append(msg)
        for index, path in enumerate(data['lessons'][policy_info.last_lesson_id].path.split(';')):
            if 1 <= index <= 2:
                msg = await bot.send_audio(
                    chat_id=data['user_id'],
                    audio=FSInputFile(path)
                )
                msg_list.append(msg)
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Если ты ознакомился с материалом, пройди тестирование 👇',
            reply_markup=await select_page_kb('📋 Пройти тест')
        )
        msg_list.append(msg)
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[0])
    elif 'какие_обзвоны' in data['lessons'][policy_info.last_lesson_id].path.split(';')[0]:
        msg_list = []
        msg = await bot.send_video(
            video=FSInputFile(data['lessons'][policy_info.last_lesson_id].path.split(';')[0]),
            chat_id=data['user_id'],
            caption=data['lessons'][policy_info.last_lesson_id].text,
            width=1080,
            height=1920
        )
        await msg_wait.delete()
        msg_list.append(msg)
        for index, path in enumerate(data['lessons'][policy_info.last_lesson_id].path.split(';')):
            if 1 <= index <= 4:
                msg = await bot.send_audio(
                    chat_id=data['user_id'],
                    audio=FSInputFile(path)
                )
                msg_list.append(msg)
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Если ты ознакомился с материалом, пройди тестирование 👇',
            reply_markup=await select_page_kb('📋 Пройти тест')
        )
        msg_list.append(msg)
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[0])
    elif 'не_делать' in data['lessons'][policy_info.last_lesson_id].path.split(';')[0]:
        msg_list = []
        msg = await bot.send_video(
            video=FSInputFile(data['lessons'][policy_info.last_lesson_id].path.split(';')[0]),
            chat_id=data['user_id'],
            caption=data['lessons'][policy_info.last_lesson_id].text,
            width=1080,
            height=1920
        )
        await msg_wait.delete()
        msg_list.append(msg)
        msg = await bot.send_audio(
            chat_id=data['user_id'],
            audio=FSInputFile(data['lessons'][policy_info.last_lesson_id].path.split(';')[1]))
        msg_list.append(msg)
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text='Если ты ознакомился с материалом, пройди тестирование 👇',
            reply_markup=await select_page_kb('📋 Пройти тест')
        )
        msg_list.append(msg)
        await state.update_data(msg_list=msg_list,
                                path=data['lessons'][policy_info.last_lesson_id].path.split(';')[1])


async def send_single_media(data, policy_info, media_path, media_type, text, text_kb, state):
    msg_media = None
    if media_type == 'mp4':
        if 600 <= data['lessons'][policy_info.last_lesson_id].id <= 670:
            width = 1920
            height = 1080
        else:
            width = 1080
            height = 1920
        msg_media = await bot.send_video(
            chat_id=data['user_id'],
            video=FSInputFile(media_path),
            width=width,
            height=height,
            request_timeout=300
        )
    elif media_type == 'png':
        msg_media = await bot.send_photo(
            chat_id=data['user_id'],
            photo=FSInputFile(media_path),
            request_timeout=300
        )
    elif media_type == 'mp3':
        msg_media = await bot.send_audio(
            chat_id=data['user_id'],
            audio=FSInputFile(media_path),
            request_timeout=300
        )

    msg = await bot.send_message(
        chat_id=data['user_id'],
        text=f'<b>{data["lessons"][policy_info.last_lesson_id].text}\n\n{text}</b>',
        disable_web_page_preview=True,
        reply_markup=await select_page_kb(text_kb)
    )
    await state.update_data(msg_media=msg_media, msg=msg, path=media_path)


async def send_test(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    lessons_list = await get_questions_by_media(data['path'], session_maker)
    user_policy_info = await get_learning_status(data['user_id'], session_maker)
    try:
        await data['msg'].delete()
    except (TelegramBadRequest, KeyError):
        pass
    try:
        await data['msg_media'].delete()
    except (TelegramBadRequest, KeyError):
        pass
    try:
        try:
            for msg in data['msg_list']:
                await msg.delete()
        except Exception:
            pass
    except Exception:
        pass

    await delete_previous_messages(data)
    logger.info(f'Try send test -- > {user_policy_info.last_lesson_id + 1} -- {len(data["lessons"])}')
    if data["count_test"] < len(lessons_list):
        formatted_message = '\n'.join(f"<code>{i + 1}.</code> {item}" for i, item in
                                      enumerate(lessons_list[data["count_test"]].
                                                answers.replace('🌟', '').replace('\n', '').split(';')))
        msg = await bot.send_message(
            chat_id=data['user_id'],
            text=f'{lessons_list[data["count_test"]].question}\n\n'
                 f'<b>Варианты ответов:</b>\n\n'
                 f'{formatted_message}',
            reply_markup=await answers_kb(lessons_list[data["count_test"]])
        )
        await state.update_data(msg=msg, question=lessons_list[data["count_test"]].question,
                                question_id=lessons_list[data["count_test"]].id,
                                true_answer=lessons_list[data["count_test"]].true_answer)
    else:
        logger.error('No more questions available, completing course')
        await update_learning_status(data['user_id'],
                                     {'last_lesson_id': user_policy_info.last_lesson_id + 1}, session_maker)

        await state.update_data(user_id=call.from_user.id, count_test=0)
        await send_lesson(session_maker, state)
        return


async def test_handle(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    user_policy_info = await get_learning_status(data['user_id'], session_maker)
    lessons_list = await get_questions_by_media(data['path'], session_maker)

    if data["count_test"] >= len(lessons_list):
        logger.error('No more questions available, completing course')
        await update_learning_status(data['user_id'],
                                     {'last_lesson_id': user_policy_info.last_lesson_id + 1}, session_maker)

        await state.update_data(user_id=call.from_user.id, count_test=0)
        await send_lesson(session_maker, state)
        return
    true_answer = lessons_list[data["count_test"]].answers.replace('🌟', '').replace('\n', '').split(';')[
        data["true_answer"] - 1]
    user_answer = lessons_list[data["count_test"]].answers.replace('🌟', '').replace('\n', '').split(';')[
        int(call.data.split(":")[3]) - 1]

    try:
        user_info = await get_user(data['user_id'], session_maker)
        if 'True' in call.data:
            await handle_correct_answer(call, user_info, data, true_answer, user_answer, user_policy_info,
                                        session_maker)
        else:
            await handle_incorrect_answer(call, user_info, data, true_answer, user_answer, user_policy_info,
                                          session_maker)

        await state.update_data(count_test=data['count_test'] + 1)
        await send_test(call, state, session_maker)
    except IndexError as _ex:
        logger.error(f'test handle error --> {_ex}')
        await update_learning_status(data['user_id'],
                                     {'last_lesson_id': user_policy_info.last_lesson_id + 1}, session_maker)
        await state.update_data(user_id=call.from_user.id, count_test=0)
        await send_lesson(session_maker, state)
        return


async def handle_correct_answer(call, user_info, data, true_answer, user_answer, user_policy_info, session_maker):
    user_policy_info = await get_learning_status(user_id=int(data['user_id']), session_maker=session_maker)

    await call.answer('✅ Есть! Идем дальше')
    await bot.send_message(
        chat_id=int(conf.admin_topic),
        message_thread_id=int(user_info.topic_id),
        text=f'<b>Пользователь верно ответил на вопрос ✅\n\n'
             f'Вопрос: {data["question"]}\n\n'
             f'Правильный ответ: <code>{true_answer}</code>\n'
             f'Ответ: <code>{user_answer}</code></b>'
    )
    await update_learning_status(data['user_id'], {'status': 'В процессе',
                                                   'user_score': user_policy_info.user_score + 1},
                                 session_maker)


async def handle_incorrect_answer(call, user_info, data, true_answer, user_answer, user_policy_info, session_maker):
    await call.answer('❌ Ух... ошибка')
    await bot.send_message(
        chat_id=int(conf.admin_topic),
        message_thread_id=int(user_info.topic_id),
        text=f'<b>Пользователь НЕ верно ответил на вопрос ❌\n\n'
             f'Вопрос: {data["question"]}\n\n'
             f'Правильный ответ: <code>{true_answer}</code>\n'
             f'Ответ: <code>{user_answer}</code></b>'
    )
    policy_info = await get_learning_status(data['user_id'], session_maker)
    await update_learning_status(data['user_id'], {
        'bad_answer_id': str(policy_info.bad_answer_id) + ';' + str(data['question_id']),
        'status': 'В процессе'}, session_maker)


def register_handler(dp: Dispatcher):
    dp.callback_query.register(send_test, F.data == 'send_test')
    dp.callback_query.register(learning_process, F.data.startswith('start_learning') & ~F.data.equals('send_test'))
    dp.callback_query.register(test_handle, F.data.startswith('test_answer'))
