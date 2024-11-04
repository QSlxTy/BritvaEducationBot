from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from integrations.database.models.new_user import get_new_user
from integrations.database.models.policy_status import is_learning_status_exists
from integrations.database.models.user import get_user


async def back_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='🔙 В главное меню', callback_data='main_menu')
    return builder.as_markup()


async def to_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='В главное меню ➡️', callback_data='main_menu')
    return builder.as_markup()


async def get_phone_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text='Поделиться номером 📲', request_contact=True)
    return builder.as_markup(resize_keyboard=True)


async def payment_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='На страницу оплаты', callback_data='payment')
    return builder.as_markup()


async def check_payment_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='Проверить платёж', callback_data='check_payment')
    return builder.as_markup()


async def choose_policy_kb(user_id, session_maker):
    builder = InlineKeyboardBuilder()
    user = await get_user(user_id, session_maker)
    if user.is_admin == 1:
        builder.button(text='✂️ Я Мастер', callback_data='barber_choose')
        builder.button(text='🤵 Я администратор', callback_data='admin_choose')
    else:
        user_info = await get_new_user(user.phone, session_maker)
        if user_info.policy == 'barber':
            builder.button(text='✂️ Я Мастер', callback_data='barber_choose')
        else:
            builder.button(text='🤵 Я администратор', callback_data='admin_choose')
    builder.button(text='🔙 В главное меню', callback_data='main_menu')
    builder.adjust(1, 1)
    return builder.as_markup()


async def answers_kb(question):
    builder = InlineKeyboardBuilder()
    for index, answer in enumerate(question.answers.split(';')):
        if '🌟' in answer:
            builder.button(
                text=f'🔘 {index + 1}',
                callback_data=f'test_answer:{question.id}:{question.policy}:{index + 1}:{True}')
        else:
            builder.button(
                text=f'🔘 {index + 1}',
                callback_data=f'test_answer:{question.id}:{question.policy}:{index + 1}:{False}')
    builder.adjust(1)
    return builder.as_markup()


async def menu_kb(session_maker, user_id):
    builder = InlineKeyboardBuilder()
    user_profile_info = await get_user(user_id, session_maker)
    if not await is_learning_status_exists(user_id, session_maker):
        builder.button(text='❔ Выбрать курс обучения', callback_data='choose_policy')
    else:
        builder.button(text='👨‍🎓 Обучение', callback_data='learning_info')

    if user_profile_info.is_admin == 1:
        builder.button(text='➖➖➖➖➖➖➖➖', callback_data=' ')
        builder.button(text='➕ Добавить урок к курсу', callback_data='add_lesson')
        builder.button(text='📋 Просмотреть список уроков', callback_data='get_list')
        builder.button(text='⚙️ Добавить администратора', callback_data='add_admin')
        builder.button(text='👨‍🎓 Добавить ученика', callback_data='add_user')

    builder.adjust(1)
    return builder.as_markup()


async def menu_learn_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='▶️ Начать', callback_data='start_learning')
    builder.button(text='◀️ Назад', callback_data='main_menu')
    builder.adjust(1)
    return builder.as_markup()


async def select_page_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='📋 Пройти тест', callback_data='send_test')
    builder.button(text='🔙 В меню', callback_data='main_menu')
    builder.adjust(1)
    return builder.as_markup()
