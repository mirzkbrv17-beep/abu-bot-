"""Lokal sinov uchun: python run_polling.py  (webhook kerak emas)"""
import asyncio
import logging

from app.bot.setup import bot, dp
from app.db.session import SessionLocal, init_db
from app.services import catalog, emoji_store, rewards


async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    async with SessionLocal() as session:
        await emoji_store.reload(session)
        await catalog.seed_defaults(session)
        await rewards.ensure_achievements(session)
        await session.commit()
    await bot.delete_webhook()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
