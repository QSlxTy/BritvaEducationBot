import random
from datetime import datetime

from sqlalchemy import BigInteger, TEXT, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker

from ..modeles import AbstractModel


class Payments(AbstractModel):
    __tablename__ = 'payments'

    telegram_id: Mapped[int] = mapped_column(BigInteger())
    date_payment: Mapped[datetime] = mapped_column(default=datetime.now())
    payment_id: Mapped[int] = mapped_column(BigInteger(), unique=True)
    status: Mapped[str] = mapped_column(TEXT, default='in process')


async def create_payment_db(telegram_id: int, payment_id: int, session_maker: sessionmaker) -> [Payments, Exception]:
    async with session_maker() as session:
        async with session.begin():
            payment = Payments(
                telegram_id=telegram_id,
                date_payment=datetime.now(),
                payment_id=payment_id,
                status='in process'
            )
            try:
                session.add(payment)
                return Payments
            except ProgrammingError as _e:
                return _e


async def get_payments_db(session_maker: sessionmaker) -> [Payments]:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(
                select(Payments))
            return result.scalars().all()


async def generate_unique_payment_id(session_maker):
    while True:
        new_payment_id = random.randint(100000, 999999)
        async with session_maker() as session:
            async with session.begin():
                result = await session.execute(
                    select(Payments).where(Payments.payment_id == new_payment_id)
                )
                if not result.scalars().first():
                    return new_payment_id
