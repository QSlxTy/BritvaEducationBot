from handlers.admin import delete_user, give_time, give_certify, add_lesson, lessons_list, add_admin, add_user


def register_admin_handler(dp):
    delete_user.register_handler(dp)
    give_time.register_handler(dp)
    give_certify.register_handler(dp)
    add_lesson.register_handler(dp)
    lessons_list.register_handler(dp)
    add_admin.register_handler(dp)
    add_user.register_handler(dp)
