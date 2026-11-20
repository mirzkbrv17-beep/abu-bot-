from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction, Wallet

CURRENCIES = ("abu_f", "abu_ton")


class InsufficientFunds(Exception):
    pass


async def _wallet(session: AsyncSession, user_id: int, currency: str, lock: bool) -> Wallet:
    q = select(Wallet).where(Wallet.user_id == user_id, Wallet.currency == currency)
    if lock:
        q = q.with_for_update()  # PostgreSQL: qatorni bloklaydi (parallel yozuvlardan himoya)
    w = (await session.execute(q)).scalar_one_or_none()
    if w is None:
        try:
            async with session.begin_nested():
                session.add(Wallet(user_id=user_id, currency=currency, balance=Decimal("0")))
                await session.flush()
        except IntegrityError:
            pass
        w = (await session.execute(q)).scalar_one()
    return w


async def get_balance(session: AsyncSession, user_id: int, currency: str) -> Decimal:
    return (await _wallet(session, user_id, currency, lock=False)).balance


async def apply_transaction(session: AsyncSession, *, user_id: int, currency: str, amount: Decimal,
                            kind: str, note: str = "", idempotency_key: str | None = None,
                            actor_tg_id: int | None = None) -> Transaction:
    """Balansni atomik o'zgartiradi va tranzaksiyani yozadi. Commit chaqiruvchida.
    Bir xil idempotency_key bilan qayta chaqirilsa, eski tranzaksiyani qaytaradi (takror yozmaydi)."""
    if currency not in CURRENCIES:
        raise ValueError("Noma'lum valyuta")
    amount = Decimal(amount)
    if amount == 0:
        raise ValueError("Summa 0 bo'lishi mumkin emas")
    if idempotency_key:
        old = (await session.execute(select(Transaction).where(
            Transaction.idempotency_key == idempotency_key))).scalar_one_or_none()
        if old:
            return old
    w = await _wallet(session, user_id, currency, lock=True)
    new_balance = w.balance + amount
    if new_balance < 0:
        raise InsufficientFunds()
    tx = Transaction(user_id=user_id, currency=currency, amount=amount, balance_after=new_balance,
                     kind=kind, note=note[:255], idempotency_key=idempotency_key, actor_tg_id=actor_tg_id)
    try:
        async with session.begin_nested():
            w.balance = new_balance
            session.add(tx)
            await session.flush()
    except IntegrityError:
        if idempotency_key:  # parallel so'rov oldin yozib qo'ygan
            await session.refresh(w)
            return (await session.execute(select(Transaction).where(
                Transaction.idempotency_key == idempotency_key))).scalar_one()
        raise
    return tx


async def history(session: AsyncSession, user_id: int, limit: int = 10) -> list[Transaction]:
    q = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.id.desc()).limit(limit)
    return list((await session.execute(q)).scalars().all())
