from aiogram.fsm.state import State, StatesGroup


class FSMPhone(StatesGroup):
    get_phone_number = State()

class FSMStart(StatesGroup):
    start_registration = State()

