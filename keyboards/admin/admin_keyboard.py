from aiogram.utils.keyboard import InlineKeyboardBuilder


async def admin_topic_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='🚫 Закрыть доступ к курсу', callback_data='user_delete')
    #builder.button(text='🪪 Выдать сертификат', callback_data='give_certify')
    builder.button(text='⌛️ Продлить доступ к курсу', callback_data='give_time')
    builder.adjust(1)
    return builder.as_markup()


async def choose_delete_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Да', callback_data='delete:yes')
    builder.button(text='❌ Нет', callback_data='delete:no')
    return builder.as_markup()


async def choose_add_user_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Да', callback_data='user_add:yes')
    builder.button(text='❌ Нет', callback_data='user_add:no')
    return builder.as_markup()


async def choose_give_time_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Да', callback_data='time:yes')
    builder.button(text='❌ Нет', callback_data='time:no')
    return builder.as_markup()


async def choose_give_certify_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Да', callback_data='certify:yes')
    builder.button(text='❌ Нет', callback_data='certify:no')
    return builder.as_markup()


async def choose_lesson_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='✂️ Для мастера', callback_data='lesson_add:barber')
    builder.button(text='🤵 Для администратора', callback_data='lesson_add:admin')
    builder.button(text='В меню', callback_data='main_menu')
    builder.adjust(2, 1)
    return builder.as_markup()


async def choose_create_kb(question):
    builder = InlineKeyboardBuilder()

    for answer in question.split(';'):
        if '🌟' in answer:
            true_answer = answer.replace('🌟', '')
            builder.button(text=f'🌟 {true_answer}',
                           callback_data=f' ')
        else:
            builder.button(text=f'🔘 {answer}',
                           callback_data=f' ')
    builder.button(text='', callback_data=' ')
    builder.button(text='✅ Да', callback_data='create:yes')
    builder.button(text='❌ Нет', callback_data='main_menu')
    builder.adjust(1)
    return builder.as_markup()


async def check_lessons_list_kb(page, len_pages):
    builder = InlineKeyboardBuilder()
    if page == 0 and len_pages == 1:
        builder.button(text='🌫', callback_data='1')
        builder.button(text='🌫', callback_data='1')
        builder.button(text='🗑 Удалить урок', callback_data='lessons_list:delete')
        builder.button(text='В меню', callback_data='main_menu')
        builder.adjust(2, 1, 1)

    elif page == (len_pages - 1):
        builder.button(text='⬅️ Назад', callback_data='lessons_list:back')
        builder.button(text='🌫', callback_data='1')
        builder.button(text='🗑 Удалить урок', callback_data='lessons_list:delete')

        builder.button(text='В меню', callback_data='main_menu')
        builder.adjust(2, 1, 1)
    elif page == 0:
        builder.button(text='🌫', callback_data='1')
        builder.button(text='Вперёд ➡️', callback_data='lessons_list:next')
        builder.button(text='🗑 Удалить урок', callback_data='lessons_list:delete')
        builder.button(text='В меню', callback_data='main_menu')
        builder.adjust(2, 1, 1)

    else:
        builder.button(text='⬅️ Назад', callback_data='lessons_list:back')
        builder.button(text='Вперёд ➡️', callback_data='lessons_list:next')
        builder.button(text='🗑 Удалить урок', callback_data='lessons_list:delete')
        builder.button(text='В меню', callback_data='main_menu')
        builder.adjust(2, 1, 1)
    return builder.as_markup()


async def choose_policy_list_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='✂️ Мастер', callback_data='lessons_list:barber')
    builder.button(text='🤵 Администратор', callback_data='lessons_list:admin')
    builder.button(text='В меню', callback_data='main_menu')
    builder.adjust(2, 1)
    return builder.as_markup()


async def create_lesson_complete_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='В меню', callback_data='main_menu')
    builder.button(text='Создать ещё', callback_data='add_lesson')
    builder.adjust(1)
    return builder.as_markup()


async def create_question_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='Закончить создание урока', callback_data='create')
    builder.button(text='Добавить ещё вопрос', callback_data='add_question')
    builder.adjust(1)
    return builder.as_markup()


async def choose_add_admin_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='✅ Да', callback_data='admin_add')
    builder.button(text='❌ Нет', callback_data='main_menu')
    builder.adjust(1)
    return builder.as_markup()


async def delete_message_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text='Удалить это сообщение', callback_data='message_delete')
    return builder.as_markup()