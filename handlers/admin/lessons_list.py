import logging

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from sqlalchemy.orm import sessionmaker

from bot_start import bot
from integrations.database.models.lessons import get_lessons, delete_lesson
from integrations.database.models.qestions import get_questions_by_media, delete_question
from keyboards.admin.admin_keyboard import check_lessons_list_kb, choose_policy_list_kb
from keyboards.user.user_keyboard import back_menu_kb


async def choose_policy_list(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    try:
        msg = await data['msg'].edit_text(
            text=f'<b>Какой тип урока вы хотите просмотреть?</b>',
            reply_markup=await choose_policy_list_kb()
        )
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(
            text=f'<b>Какой тип урока вы хотите просмотреть</b>',
            reply_markup=await choose_policy_list_kb()
        )
    await state.update_data(msg=msg)


async def check_lessons_list(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    await state.update_data(policy_list=call.data.split(':')[1])
    data = await state.get_data()

    lessons_list = await get_lessons(data['policy_list'], session_maker)
    if 'next' in call.data:
        await state.update_data(current_lesson=data['current_lesson'] + 1)
    elif 'back' in call.data:
        await state.update_data(current_lesson=data['current_lesson'] - 1)
    else:
        await state.update_data(lessons=lessons_list, current_lesson=0, user_id=call.from_user.id)
    if 'delete' in call.data:
        list_delete = await get_questions_by_media(data['path'], session_maker)
        for delete in list_delete:
            await delete_question(delete.path, session_maker)
        await delete_lesson(data['path'], session_maker)
        msg = await bot.send_message(chat_id=call.from_user.id,
                                     text='<b>Урок успешно удалён ♻️</b>')
        await state.update_data(msg=msg, current_lesson=0)
    await send_lesson_list(call.from_user.id, state)


async def send_lesson_list(chat_id: int, state: FSMContext):
    data = await state.get_data()
    try:
        await data['msg'].delete()
    except TelegramBadRequest:
        pass
    try:
        msg_wait = await bot.send_message(text='<b>Файл слишком большой, отправляю, ожидайте ⏳</b>',
                                          chat_id=data['user_id'])
        if 'mp4' in data['lessons'][data['current_lesson']].path:
            msg = await bot.send_video(
                chat_id=data['user_id'],
                video=FSInputFile(data['lessons'][data['current_lesson']].path),
                caption=f'<b>{data["lessons"][data["current_lesson"]].text}\n\n</b>'
                        f'\n\n',
                reply_markup=await check_lessons_list_kb(data['current_lesson'],
                                                         len(data['lessons'])),
                request_timeout=300)

        else:
            msg = await bot.send_photo(
                chat_id=data['user_id'],
                photo=FSInputFile(data['lessons'][data['current_lesson']].path),
                caption=f'<b>{data["lessons"][data["current_lesson"]].text}\n\n</b>'
                        f'\n\n',
                reply_markup=await check_lessons_list_kb(data['current_lesson'],
                                                         len(data['lessons'])),
                request_timeout=300)

        await state.update_data(msg=msg, text=data["lessons"][data["current_lesson"]].text,
                                path=data["lessons"][data["current_lesson"]].path)
        await msg_wait.delete()
    except IndexError as _ex:
        try:
            msg = await data['msg'].edit_text(text=f'<b>Уроков пока нет</b>',
                                              reply_markup=await back_menu_kb())
        except TelegramBadRequest:
            msg = await bot.send_message(text=f'<b>Уроков пока нет</b>',
                                         chat_id=data['user_id'],
                                         reply_markup=await back_menu_kb())
    await state.update_data(msg=msg)


def register_handler(dp: Dispatcher):
    dp.callback_query.register(choose_policy_list, F.data == 'get_list')
    dp.callback_query.register(check_lessons_list, F.data.startswith('lessons_list'))
