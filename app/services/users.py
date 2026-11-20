import secrets
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import User
from app.services import wallet


async def _new_abu_id(session: AsyncSession) -> str:
    while True:
        candidate = f"ABU{secrets.randbelow(10**7):07d}"
        exists = (await session.execute(select(User.id).where(User.abu_id == candidate))).first()
        if not exists:
            return candidate


async def get_by_tg(session: AsyncSession, tg_id: int) -> User | None:
    return (await session.execute(select(User).where(User.tg_id == tg_id))).scalar_one_or_none()


async def get_or_create(session: AsyncSession, tg_user, referrer_tg_id: int | None = None) -> tuple[User, bool]:
    user = await get_by_tg(session, tg_user.id)
    if user:
        user.username, user.first_name = tg_user.username, tg_user.first_name or ""
        return user, False
    referrer = None
    if referrer_tg_id and referrer_tg_id != tg_user.id:
        referrer = await get_by_tg(session, referrer_tg_id)
    user = User(tg_id=tg_user.id, abu_id=await _new_abu_id(session), username=tg_user.username,
                first_name=tg_user.first_name or "", referrer_id=referrer.id if referrer else None)
    try:
        async with session.begin_nested():
            session.add(user)
            await session.flush()
    except IntegrityError:  # parallel /start
        return await get_by_tg(session, tg_user.id), False
    for cur in wallet.CURRENCIES:
        await wallet._wallet(session, user.id, cur, lock=False)
    bonus = get_settings().referral_bonus_abu_f
    if referrer and bonus > Decimal(0):
        await wallet.apply_transaction(session, user_id=referrer.id, currency="abu_f", amount=bonus,
                                       kind="referral", note=f"Referal: {user.abu_id}",
                                       idempotency_key=f"ref:{user.id}")
    return user, True


async def referral_count(session: AsyncSession, user_id: int) -> int:
    return (await session.execute(select(func.count(User.id)).where(User.referrer_id == user_id))).scalar_one()


async def top_by_xp(session: AsyncSession, limit: int = 10) -> list[User]:
    q = select(User).where(User.is_banned.is_(False)).order_by(User.xp.desc(), User.id).limit(limit)
    return list((await session.execute(q)).scalars().all())
