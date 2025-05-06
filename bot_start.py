import logging

from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from src.bot.dispatcher import get_dispatcher
from aiogram.client.default import DefaultBotProperties

from src.config import conf
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot

session = AiohttpSession(
    api=TelegramAPIServer.from_base('http://localhost:8081'))
bot = Bot(token=conf.bot.token, default=DefaultBotProperties(parse_mode='HTML'), session=session)
storage = MemoryStorage()
logger = logging.getLogger(__name__)
dp = get_dispatcher(storage=storage)
