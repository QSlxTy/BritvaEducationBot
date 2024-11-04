from handlers.user import start, registration, choose_policy, learn_menu, learning


def register_user_handler(dp):
    start.register_start_handler(dp)
    registration.register_handler(dp)
    choose_policy.register_handler(dp)
    learn_menu.register_handler(dp)
    learning.register_handler(dp)
