from aiogram.fsm.state import State, StatesGroup


class FSMTopic(StatesGroup):
    give_time = State()


class FSMCreate(StatesGroup):
    add_lesson = State()
    give_test_lesson = State()
    give_answers = State()
    pre_check_lesson = State()


class FSMAddAdmin(StatesGroup):
    add_admin = State()


class FSMReg(StatesGroup):
    verify_phone = State()


class FSMAddUser(StatesGroup):
    add_user = State()
