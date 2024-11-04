from datetime import datetime

from sqlalchemy import select, BigInteger, update, TEXT, delete
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column

from ..modeles import AbstractModel


class User(AbstractModel):
    __tablename__ = 'users'

    telegram_id: Mapped[int] = mapped_column(BigInteger(), unique=True)
    telegram_username: Mapped[str] = mapped_column(TEXT, default=None)
    telegram_fullname: Mapped[str] = mapped_column(TEXT, default=None)
    user_fio: Mapped[str] = mapped_column(TEXT, default='0')
    date_registration: Mapped[datetime] = mapped_column()
    topic_id: Mapped[int] = mapped_column(BigInteger(), unique=True)
    phone: Mapped[str] = mapped_column(TEXT, default='Не указан')
    verify: Mapped[bool] = mapped_column(default=False)
    access: Mapped[bool] = mapped_column(default=True)
    is_admin: Mapped[bool] = mapped_column(default=False)


async def get_user(user_id: int, session_maker: sessionmaker) -> User:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.telegram_id == user_id))
            return result.scalars().one()


async def get_user_by_username(username: str, session_maker: sessionmaker) -> User:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(User.telegram_username == username))
            return result.scalars().one()


async def get_user_dict(select_by: dict, session_maker: sessionmaker) -> User:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(
                select(User).filter_by(**select_by)
            )
            return result.scalars().one()


async def create_user(user_id: int, username: str, topic_id: int, telegram_fullname: str,
                      session_maker: sessionmaker) -> [User, Exception]:
    async with session_maker() as session:
        async with session.begin():
            user = User(
                telegram_id=user_id,
                telegram_username=username,
                topic_id=topic_id,
                telegram_fullname=telegram_fullname,
                date_registration=datetime.now()
            )
            try:
                session.add(user)
                return User
            except ProgrammingError as _e:
                return _e


async def is_user_exists(user_id: int, session_maker: sessionmaker) -> bool:
    async with session_maker() as session:
        async with session.begin():
            sql_res = await session.execute(select(User).where(User.telegram_id == user_id))
            return bool(sql_res.first())


async def is_user_exists_by_username(username: str, session_maker: sessionmaker) -> bool:
    async with session_maker() as session:
        async with session.begin():
            sql_res = await session.execute(select(User).where(User.telegram_username == username))
            return bool(sql_res.first())


async def update_user(telegram_id: int, data: dict, session_maker: sessionmaker) -> None:
    async with session_maker() as session:
        async with session.begin():
            await session.execute(update(User).where(User.telegram_id == telegram_id).values(data))
            await session.commit()


async def get_users(session_maker: sessionmaker) -> User:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(select(User))
            return result.scalars().all()


async def delete_user_db(user_id: int, session_maker: sessionmaker):
    async with session_maker() as session:
        async with session.begin():
            await session.execute(delete(User).where(User.telegram_id == user_id))
            await session.commit()
