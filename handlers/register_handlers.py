from handlers.admin.register_admin_handlers import register_admin_handler
from handlers.user.register_user_handlers import register_user_handler
from handlers.other import register_other_handlers


async def register_handlers(dp):
    register_user_handler(dp)
    register_admin_handler(dp)
    register_other_handlers(dp)
