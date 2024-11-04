import sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine
from sqlalchemy.orm import sessionmaker

from integrations.database.models.lessons import Lessons
from integrations.database.models.new_user import NewReg
from integrations.database.models.payments import Payments
from integrations.database.models.policy_status import PolicyStatus
from integrations.database.models.qestions import Questions
from integrations.database.models.user import User
from src.config import conf


def get_session_maker(engine: sqlalchemy.ext.asyncio.AsyncEngine) -> sessionmaker:
    return sessionmaker(engine, class_=sqlalchemy.ext.asyncio.AsyncSession, expire_on_commit=False)


async def create_connection() -> sqlalchemy.ext.asyncio.AsyncEngine:
    url = conf.db.build_connection_str()

    engine = _create_async_engine(
        url=url, pool_pre_ping=True)
    return engine


class Database:
    def __init__(
            self,
            session: AsyncSession,
            user: User = None,
            policy_status: PolicyStatus = None,
            lessons: Lessons = None,
            questions: Questions = None,
            payments: Payments = None,
            new_user: NewReg = None
    ):
        self.session = session
        self.user = user or User()
        self.policy_status = policy_status or PolicyStatus()
        self.lessons = lessons or Lessons()
        self.questions = questions or Questions()
        self.payments = payments or Payments()
        self.new_user = new_user or NewReg()


async def init_models(engine):
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all)
        await conn.run_sync(PolicyStatus.metadata.create_all)
        await conn.run_sync(Lessons.metadata.create_all)
        await conn.run_sync(Questions.metadata.create_all)
        await conn.run_sync(Payments.metadata.create_all)
        await conn.run_sync(NewReg.metadata.create_all)
