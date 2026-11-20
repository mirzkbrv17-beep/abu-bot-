from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import Base

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Jadvallarni yaratadi (bo'lsa tegmaydi). Keyingi o'zgarishlar uchun Alembic ishlatiladi."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
