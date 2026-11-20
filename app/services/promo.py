from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PromoCode, PromoRedemption, User
from app.services import wallet


class PromoError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato."""


def normalize(code: str) -> str:
    return (code or "").strip().upper()


async def redeem(session: AsyncSession, user: User, raw_code: str, now: datetime | None = None) -> Decimal:
    code = normalize(raw_code)
    if not code or len(code) > 32:
        raise PromoError("Promo-kod noto‘g‘ri.")
    promo = (await session.execute(select(PromoCode).where(PromoCode.code == code))).scalar_one_or_none()
    now = now or datetime.now(timezone.utc)
    if not promo or not promo.is_active:
        raise PromoError("Promo-kod topilmadi yoki faol emas.")
    exp = promo.expires_at
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= now:
            raise PromoError("Promo-kod muddati tugagan.")
    try:
        async with session.begin_nested():
            # Limitni atomik oshiramiz: shart bajarilmasa, qatorga tegilmaydi.
            res = await session.execute(
                update(PromoCode)
                .where(PromoCode.id == promo.id, PromoCode.is_active.is_(True),
                       PromoCode.max_uses.is_(None) | (PromoCode.used_count < PromoCode.max_uses))
                .values(used_count=PromoCode.used_count + 1)
                .execution_options(synchronize_session=False))
            if res.rowcount != 1:
                raise PromoError("Promo-kod limiti tugagan.")
            session.add(PromoRedemption(promo_id=promo.id, user_id=user.id))
            await session.flush()
    except IntegrityError:
        raise PromoError("Siz bu promo-kodni allaqachon ishlatgansiz.")
    await wallet.apply_transaction(session, user_id=user.id, currency=promo.currency,
                                   amount=Decimal(promo.amount), kind="promo",
                                   note=f"Promo-kod: {promo.code}",
                                   idempotency_key=f"promo:{promo.id}:{user.id}")
    return Decimal(promo.amount)
