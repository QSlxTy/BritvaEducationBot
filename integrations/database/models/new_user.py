from datetime import datetime

from sqlalchemy import TEXT, select, update, delete
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column

from ..modeles import AbstractModel


class NewReg(AbstractModel):
    __tablename__ = 'new_registration'

    phone: Mapped[str] = mapped_column(TEXT)
    policy: Mapped[str] = mapped_column(TEXT)
    date_registration: Mapped[datetime] = mapped_column()
    verify_access: Mapped[bool] = mapped_column()


async def create_phone(phone: str, policy: str, session_maker: sessionmaker) -> [NewReg, Exception]:
    async with session_maker() as session:
        async with session.begin():
            user = NewReg(
                phone=phone,
                policy=policy,
                verify_access=False,
                date_registration=datetime.now()
            )
            try:
                session.add(user)
                return NewReg
            except ProgrammingError as _e:
                return _e


async def get_new_user(phone: int, session_maker: sessionmaker) -> NewReg:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(
                select(NewReg).where(NewReg.phone == phone))
            return result.scalars().one()


async def update_new_user(phone: int, data: dict, session_maker: sessionmaker) -> None:
    async with session_maker() as session:
        async with session.begin():
            await session.execute(update(NewReg).where(NewReg.phone == phone).values(data))
            await session.commit()


async def is_phone_exists(phone: str, session_maker: sessionmaker) -> bool:
    async with session_maker() as session:
        async with session.begin():
            sql_res = await session.execute(select(NewReg).where(NewReg.phone == phone))
            return bool(sql_res.first())


async def delete_newreg(phone: str, session_maker: sessionmaker):
    async with session_maker() as session:
        async with session.begin():
            await session.execute(delete(NewReg).where(NewReg.phone == phone))
            await session.commit()
