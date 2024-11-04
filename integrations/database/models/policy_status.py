from datetime import datetime

from sqlalchemy import BigInteger, TEXT, select, update, delete
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker

from ..modeles import AbstractModel


class PolicyStatus(AbstractModel):
    __tablename__ = 'policy_status'

    telegram_id: Mapped[int] = mapped_column(BigInteger(), unique=True)
    date_start: Mapped[datetime] = mapped_column(default=datetime.now())
    policy: Mapped[str] = mapped_column(TEXT)
    user_score: Mapped[int] = mapped_column(BigInteger(), default=0)
    last_lesson_id: Mapped[int] = mapped_column(BigInteger(), default=0)
    status: Mapped[str] = mapped_column(TEXT, default='Не начинал')
    count_try: Mapped[int] = mapped_column(BigInteger(), default=3)


async def get_learning_status(user_id: int, session_maker: sessionmaker) -> PolicyStatus:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(
                select(PolicyStatus).where(PolicyStatus.telegram_id == user_id))
            return result.scalars().one()


async def learning_status(telegram_id: int, policy: str, session_maker: sessionmaker) -> [PolicyStatus, Exception]:
    async with session_maker() as session:
        async with session.begin():
            policy = PolicyStatus(
                telegram_id=telegram_id,
                policy=policy,
                user_score=0,
                status='Начат'
            )
            try:
                session.add(policy)
                return PolicyStatus
            except ProgrammingError as _e:
                return _e


async def is_learning_status_exists(telegram_id: int, session_maker: sessionmaker) -> bool:
    async with session_maker() as session:
        async with session.begin():
            sql_res = await session.execute(select(PolicyStatus).where(PolicyStatus.telegram_id == telegram_id))
            return bool(sql_res.first())


async def update_learning_status(telegram_id: int, data: dict, session_maker: sessionmaker) -> None:
    async with session_maker() as session:
        async with session.begin():
            await session.execute(update(PolicyStatus).where(PolicyStatus.telegram_id == telegram_id).values(data))
            await session.commit()


async def delete_policy(user_id: int, session_maker: sessionmaker):
    async with session_maker() as session:
        async with session.begin():
            await session.execute(delete(PolicyStatus).where(PolicyStatus.telegram_id == user_id))
            await session.commit()
