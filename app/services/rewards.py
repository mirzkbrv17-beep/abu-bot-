"""Kunlik bonus, streak, VIP, daraja (level) va yutuqlar. Barcha qoidalar shu yerda."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Achievement, User, UserAchievement
from app.services import wallet

LEVEL_XP = 100
DAILY_BASE = Decimal("10")
DAILY_STREAK_BONUS = Decimal("2")   # har kun uchun qo‘shimcha
DAILY_STREAK_CAP = 30               # streak bonusi 30 kundan oshmaydi
DAILY_XP = 15
VIP_PRICE_PER_MONTH = Decimal("1000")  # ABU F
VIP_MULTIPLIER = Decimal("2")

ACHIEVEMENTS = [
    dict(code="first_daily", title="Birinchi kun", emoji="🌅", reward_abu_f=Decimal("20")),
    dict(code="streak_7", title="Haftalik olov", emoji="🔥", reward_abu_f=Decimal("100")),
    dict(code="streak_30", title="Oylik sadoqat", emoji="💠", reward_abu_f=Decimal("500")),
    dict(code="level_5", title="5-daraja", emoji="📈", reward_abu_f=Decimal("150")),
    dict(code="first_referral", title="Birinchi do‘st", emoji="👥", reward_abu_f=Decimal("30")),
    dict(code="vip_member", title="VIP a’zo", emoji="👑", reward_abu_f=Decimal("50")),
]


class RewardError(Exception):
    """Foydalanuvchiga ko‘rsatiladigan xato."""


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def is_vip(user: User, now: datetime | None = None) -> bool:
    until = _aware(user.vip_until)
    return bool(until and until > (now or datetime.now(timezone.utc)))


def daily_reward(streak: int, vip: bool) -> Decimal:
    base = DAILY_BASE + DAILY_STREAK_BONUS * min(streak, DAILY_STREAK_CAP)
    return base * (VIP_MULTIPLIER if vip else Decimal("1"))


async def claim_daily(session: AsyncSession, user: User, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    today = now.date()
    last = _aware(user.last_daily_at)
    if last and last.date() == today:
        raise RewardError("Bugungi bonus allaqachon olingan. Ertaga qayting.")
    yesterday = today - timedelta(days=1)
    user.streak = user.streak + 1 if (last and last.date() == yesterday) else 1
    user.last_daily_at = now
    vip = is_vip(user, now)
    amount = daily_reward(user.streak, vip)
    await wallet.apply_transaction(session, user_id=user.id, currency="abu_f", amount=amount,
                                   kind="daily", note=f"Kunlik bonus ({user.streak}-kun)",
                                   idempotency_key=f"daily:{user.id}:{today.isoformat()}")
    await add_xp(session, user, DAILY_XP)
    granted = await check_achievements(session, user)
    return {"amount": amount, "streak": user.streak, "vip": vip, "achievements": granted}


async def add_xp(session: AsyncSession, user: User, xp: int) -> None:
    user.xp += xp
    user.level = user.xp // LEVEL_XP + 1


async def buy_vip(session: AsyncSession, user: User, months: int, now: datetime | None = None) -> datetime:
    if months not in (1, 3, 12):
        raise RewardError("VIP muddati: 1, 3 yoki 12 oy.")
    now = now or datetime.now(timezone.utc)
    cost = VIP_PRICE_PER_MONTH * months
    if months == 3:
        cost = cost * Decimal("0.9")
    if months == 12:
        cost = cost * Decimal("0.8")
    try:
        await wallet.apply_transaction(session, user_id=user.id, currency="abu_f", amount=-cost,
                                       kind="vip", note=f"VIP {months} oy",
                                       idempotency_key=f"vip:{user.id}:{now.isoformat()}")
    except wallet.InsufficientFunds:
        raise RewardError("ABU F yetarli emas.")
    base = max(_aware(user.vip_until) or now, now)
    user.vip_until = base + timedelta(days=30 * months)
    await check_achievements(session, user)
    return user.vip_until


async def ensure_achievements(session: AsyncSession) -> None:
    if (await session.execute(select(func.count(Achievement.id)))).scalar_one() > 0:
        return
    for a in ACHIEVEMENTS:
        session.add(Achievement(**a))
    await session.flush()


async def _unlocked(session: AsyncSession, user: User) -> set[str]:
    rows = await session.execute(select(Achievement.code).join(
        UserAchievement, UserAchievement.achievement_id == Achievement.id).where(UserAchievement.user_id == user.id))
    return set(rows.scalars().all())


def _conditions(user: User, refs: int) -> dict[str, bool]:
    return {
        "first_daily": user.last_daily_at is not None,
        "streak_7": user.streak >= 7,
        "streak_30": user.streak >= 30,
        "level_5": user.level >= 5,
        "first_referral": refs >= 1,
        "vip_member": is_vip(user),
    }


async def check_achievements(session: AsyncSession, user: User) -> list[str]:
    """Shartlari bajarilgan, lekin hali berilmagan yutuqlarni beradi. Berilganlar nomini qaytaradi."""
    from app.services.users import referral_count
    await ensure_achievements(session)
    done = await _unlocked(session, user)
    cond = _conditions(user, await referral_count(session, user.id))
    granted = []
    for code, ok in cond.items():
        if not ok or code in done:
            continue
        ach = (await session.execute(select(Achievement).where(Achievement.code == code))).scalar_one()
        try:
            async with session.begin_nested():
                session.add(UserAchievement(user_id=user.id, achievement_id=ach.id))
                await session.flush()
        except IntegrityError:
            continue
        if ach.reward_abu_f > 0:
            await wallet.apply_transaction(session, user_id=user.id, currency="abu_f", amount=ach.reward_abu_f,
                                           kind="achievement", note=f"Yutuq: {ach.title}",
                                           idempotency_key=f"ach:{ach.code}:{user.id}")
        granted.append(f"{ach.emoji} {ach.title}")
    return granted
