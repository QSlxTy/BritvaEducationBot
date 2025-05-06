import logging
import os

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.lessons import create_lesson_db
from integrations.database.models.qestions import create_question
from keyboards.admin.admin_keyboard import choose_lesson_kb, create_lesson_complete_kb, create_question_kb
from keyboards.user.user_keyboard import back_menu_kb
from utils.states.admin import FSMCreate


async def choose_add_lesson(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        msg = await data['msg'].edit_text(
            text=f'<b>Какой тип урока вы хотите добавить?</b>',
            reply_markup=await choose_lesson_kb()
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        msg = await call.message.answer(
            text=f'<b>Какой тип урока вы хотите добавить?</b>',
            reply_markup=await choose_lesson_kb()
        )

    await state.update_data(msg=msg)


async def add_lesson(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(FSMCreate.add_lesson)
    data = await state.get_data()
    try:
        msg = await data['msg'].edit_text(
            text=f'<b>Отправьте медифайл</b>\n\n'
                 f'*<i>Вы так же можете отправить фото/видео с описанием</i>',
            reply_markup=await back_menu_kb()
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(
            text=f'<b>Отправьте медифайл</b>\n\n'
                 f'*<i>Вы так же можете отправить фото/видео с описанием</i>',
            reply_markup=await back_menu_kb()
        )
    await state.update_data(msg=msg, lesson=call.data.split(':')[1])


async def give_test_lesson(message: types.Message, state: FSMContext):
    await state.set_state(FSMCreate.give_test_lesson)
    data = await state.get_data()
    await data['msg'].delete()
    msg = await message.answer(
        text='<b>Идёт скачивание, ожидайте ⏳</b>'
    )
    if not os.path.exists(f'media'):
        os.makedirs(f'media')
    if message.photo:
        file_info = await bot.get_file(message.photo[-1].file_id, request_timeout=300)
        await state.update_data(destination=file_info.file_path, caption=message.caption)
        await state.update_data(caption=message.caption)
    elif message.video:
        file_info = await bot.get_file(message.video.file_id, request_timeout=300)
        await state.update_data(destination=file_info.file_path, caption=message.caption)
        await state.update_data(caption=message.caption)
    else:
        await state.update_data(caption=message.text)
    await msg.delete()
    await message.delete()
    try:
        msg = await bot.send_message(
            chat_id=message.from_user.id,
            text=f'<b>Введите вопрос для теста</b>'
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        msg = await message.answer(
            text=f'<b>Введите вопрос для теста<</b>'
        )
    await state.update_data(msg=msg)


async def give_answers(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(FSMCreate.give_test_lesson)
    data = await state.get_data()
    try:
        msg = await data['msg'].edit_text(
            text=f'<b>Введите вопрос для теста</b>'
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(
            text=f'<b>Введите вопрос для теста</b>'
        )
    await state.update_data(msg=msg)


async def pre_check_lesson(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(FSMCreate.pre_check_lesson)
    await message.delete()
    try:
        msg = await data['msg'].edit_text(
            text=f'<b>Введите варианты ответа через запятую, без пробелов, '
                 f'рядом с верным ответом поставьте эмодзи🌟\n\n</b>'
                 f'Пример <code>ответ1,🌟верный_ответ2,ответ3</code>'
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        msg = await message.answer(
            text=f'<b>Введите варианты ответа через запятую, без пробелов, '
                 f'рядом с верным ответом поставьте эмодзи🌟\n\n</b>'
                 f'Пример <code>ответ1,🌟верный_ответ2,ответ3</code>'
        )
    await state.update_data(msg=msg, question=message.text)


async def answer_handle(message: types.Message, state: FSMContext, session_maker: sessionmaker):
    question_list = message.text.split(';')
    for index, question in enumerate(question_list):
        if '🌟' in question:
            await state.update_data(true_answer=int(index + 1))
            break
    await state.update_data(answers=message.text.replace('\n', ''))
    data = await state.get_data()
    await message.delete()
    try:
        msg = await data['msg'].edit_text(
            text=f'<b>Вопрос:\n'
                 f'{data["question"]}\n\n'
                 f'Варианты ответа:\n'
                 f'{message.text}\n\n'
                 f'Правильный ответ:\n'
                 f'{data["true_answer"]}</b>',
            reply_markup=await create_question_kb()
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        msg = await message.answer(
            text=f'<b>Вопрос:\n'
                 f'{data["question"]}\n\n'
                 f'Варианты ответа:\n'
                 f'{message.text}\n\n'
                 f'Правильный ответ:\n'
                 f'{data["true_answer"]}</b>',
            reply_markup=await create_question_kb()
        )
    await create_question(data['destination'], data["question"],
                          message.text, data["true_answer"], data['lesson'], session_maker)

    await state.update_data(msg=msg)


async def choose_create(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    try:
        msg = await data['msg'].edit_text(
            text=f'<b>Урок создан</b>',
            reply_markup=await create_lesson_complete_kb()
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(
            text=f'<b>Урок создан</b>',
            reply_markup=await create_lesson_complete_kb()
        )
    await state.update_data(msg=msg)
    if data['caption'] is None:
        await state.update_data(caption='⏳')
    data = await state.get_data()
    await create_lesson_db(data['destination'], data['caption'], data['lesson'], session_maker)


def register_handler(dp: Dispatcher):
    dp.callback_query.register(choose_add_lesson, F.data == 'add_lesson')
    dp.callback_query.register(add_lesson, F.data.startswith('lesson_add'))
    dp.message.register(give_test_lesson, FSMCreate.add_lesson, F.content_type.in_({'photo', 'text', 'video'}))
    dp.callback_query.register(choose_create, F.data.startswith('create'))
    dp.message.register(pre_check_lesson, FSMCreate.give_test_lesson, F.content_type == 'text')
    dp.message.register(answer_handle, FSMCreate.pre_check_lesson, F.content_type == 'text')
    dp.callback_query.register(give_answers, F.data == 'add_question')
