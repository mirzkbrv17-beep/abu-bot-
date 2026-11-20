from aiogram import BaseMiddleware
from sqlalchemy import select

from app.db.models import User
from app.db.session import SessionLocal
from app.services import emoji_store
from app.services.emoji import emoji


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with SessionLocal() as session:
            data["session"] = session
            if emoji.is_stale():
                await emoji_store.reload(session)
            data["db_user"] = None
            tg_user = data.get("event_from_user")
            if tg_user:
                u = (await session.execute(select(User).where(User.tg_id == tg_user.id))).scalar_one_or_none()
                if u and u.is_banned:
                    return None
                data["db_user"] = u
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
