from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot import errors
from app.bot.handlers import admin, market, menu, rewards, shop, start, tasks
from app.bot.middleware import DbSessionMiddleware
from app.config import get_settings

bot = Bot(get_settings().bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.update.outer_middleware(DbSessionMiddleware())
dp.include_routers(errors.router, admin.router, start.router, shop.router, tasks.router, rewards.router, market.router, menu.router)
