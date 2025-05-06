from sqlalchemy import TEXT, select, func, BigInteger
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column

from ..modeles import AbstractModel


class Questions(AbstractModel):
    __tablename__ = 'questions'

    path: Mapped[str] = mapped_column(TEXT)
    question: Mapped[str] = mapped_column(TEXT)
    answers: Mapped[str] = mapped_column(TEXT)
    true_answer: Mapped[int] = mapped_column(BigInteger())
    policy: Mapped[str] = mapped_column(TEXT)


async def get_questions_by_media(lesson: str, session_maker: sessionmaker) -> [Questions]:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(select(Questions).where(Questions.path == lesson))
            return result.scalars().all()


async def get_count_questions(session_maker: sessionmaker, policy):
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(
                select(func.count()).select_from(Questions).where(Questions.policy == policy))
            return result.scalar()


async def create_question(path: str, question: str, answers: str, true_answer: str, policy: str,
                          session_maker: sessionmaker) -> [Questions, Exception]:
    async with session_maker() as session:
        async with session.begin():
            user = Questions(
                path=path,
                question=question,
                answers=answers,
                true_answer=true_answer,
                policy=policy,
            )
            try:
                session.add(user)
                return Questions
            except ProgrammingError as _ex:
                return _ex


async def delete_question(path: str, session_maker: sessionmaker):
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(select(Questions).where(Questions.path == path))
            await session.delete(result.scalars().first())
            await session.commit()

async def get_question_by_id(question_id: int, session_maker: sessionmaker) -> Questions:
    async with session_maker() as session:
        async with session.begin():
            result = await session.execute(select(Questions).where(Questions.id == question_id))
            return result.scalars().one()