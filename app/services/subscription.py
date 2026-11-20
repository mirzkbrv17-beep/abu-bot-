import logging

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RequiredChannel

log = logging.getLogger(__name__)
OK_STATUSES = {"member", "administrator", "creator"}


async def missing_channels(bot: Bot, session: AsyncSession, tg_id: int) -> list[RequiredChannel]:
    channels = (await session.execute(select(RequiredChannel).where(RequiredChannel.is_active.is_(True)))).scalars().all()
    missing = []
    for ch in channels:
        try:
            m = await bot.get_chat_member(ch.chat_id, tg_id)
            if m.status in OK_STATUSES or (m.status == "restricted" and getattr(m, "is_member", False)):
                continue
            missing.append(ch)
        except Exception as e:  # bot kanalda admin emas va hokazo: foydalanuvchini to'smaymiz
            log.warning("Kanal tekshirib bo'lmadi %s: %s", ch.chat_id, e)
    return missing
