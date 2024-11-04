import logging

from aiogram import types, F, Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from sqlalchemy.orm import sessionmaker

from integrations.database.models.new_user import delete_newreg
from integrations.database.models.policy_status import delete_policy
from integrations.database.models.user import get_user_dict, delete_user_db
from keyboards.admin.admin_keyboard import choose_delete_kb, admin_topic_kb


async def choose_delete_user(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    user_info = await get_user_dict({'topic_id': call.message.message_thread_id}, session_maker)
    try:
        msg = await data['msg'].edit_text(f'<b>Вы точно хотите закрыть доступ к курсу пользователю...\n\n'
                                          f'ФИО: <code>{user_info.user_fio}</code>\n'
                                          f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                          f'Имя: <code>{user_info.telegram_fullname}</code>\n</b>',
                                          reply_markup=await choose_delete_kb())
    except (TelegramBadRequest, KeyError) as _ex:
        logging.error(_ex)
        await call.message.delete()
        msg = await call.message.answer(f'<b>Вы точно хотите закрыть доступ к курсу пользователю...\n\n'
                                        f'ФИО: <code>{user_info.user_fio}</code>\n'
                                        f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                        f'Имя: <code>{user_info.telegram_fullname}</code>\n</b>',
                                        reply_markup=await choose_delete_kb())

    await state.update_data(msg=msg)


async def delete_user(call: types.CallbackQuery, state: FSMContext, session_maker: sessionmaker):
    data = await state.get_data()
    user_info = await get_user_dict({'topic_id': call.message.message_thread_id}, session_maker)
    if 'yes' in call.data:
        try:
            msg = await data['msg'].edit_text(f'<b>Пользователю...'
                                              f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                              f'Имя: <code>{user_info.telegram_fullname}</code>\n\n'
                                              f'...Был закрыт доступ к курсу ❌</b>')
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(f'<b>Пользователю...'
                                            f'ID в ТГ: <code>{user_info.telegram_id}</code>\n'
                                            f'Имя: <code>{user_info.telegram_fullname}</code>\n\n'
                                            f'...Был закрыт доступ к курсу ❌</b>')
        await delete_user_db(user_info.telegram_id, session_maker)
        await delete_policy(user_info.telegram_id, session_maker)
        await delete_newreg(user_info.phone, session_maker)
    else:
        try:
            msg = await data['msg'].edit_text(f'<b>Вы отменили процесс закрытия курса ⭕️ /start</b>')
        except (TelegramBadRequest, KeyError) as _ex:
            logging.error(_ex)
            await call.message.delete()
            msg = await call.message.answer(f'<b>Вы отменили процесс закрытия курса ⭕️ /start</b>')
    await state.update_data(msg=msg)


def register_handler(dp: Dispatcher):
    dp.callback_query.register(choose_delete_user, F.data == 'user_delete')
    dp.callback_query.register(delete_user, F.data.startswith('delete'))
