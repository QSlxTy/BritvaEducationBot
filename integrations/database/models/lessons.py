from sqlalchemy import TEXT, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column

from ..modeles import AbstractModel


class Lessons(AbstractModel):
    __tablename__ = 'lessons'

    path: Mapped[str] = mapped_column(TEXT)
    text: Mapped[str] = mapped_column(TEXT)
    policy: Mapped[str] = mapped_column(TEXT)


async def get_lessons(policy: str, session_maker: sessionmaker) -> [Lessons]:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(select(Lessons).where(Lessons.policy == policy))
            return result.scalars().all()


async def create_lesson_db(path: str, text: str, policy: str,
                           session_maker: sessionmaker) -> [Lessons, Exception]:
    async with session_maker() as session:
        async with session.begin():
            user = Lessons(
                path=path,
                text=text,
                policy=policy,
            )
            try:
                session.add(user)
                return Lessons
            except ProgrammingError as _e:
                return _e


async def delete_lesson(path: str, session_maker: sessionmaker):
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(select(Lessons).where(Lessons.path == path))
            await session.delete(result.scalars().first())
            await session.commit()


async def get_lesson_by_id(lesson_id: str, session_maker: sessionmaker) -> Lessons:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(select(Lessons).where(Lessons.id == lesson_id))
            return result.scalars().one()


async def get_lesson_by_media(lesson: str, session_maker: sessionmaker) -> [Lessons]:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(select(Lessons).where(Lessons.path == lesson))
            return result.scalars().all()
