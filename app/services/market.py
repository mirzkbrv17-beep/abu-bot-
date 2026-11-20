"""Foydalanuvchilar o'rtasidagi bozor. Pul va buyum bitta atomik tranzaksiyada almashadi."""
from decimal import Decimal, ROUND_DOWN

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import InventoryItem, Listing, Product
from app.services import wallet


class MarketError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato."""


def fee_for(price: Decimal) -> Decimal:
    pct = get_settings().market_fee_percent
    return (price * pct / Decimal(100)).quantize(Decimal("0.0001"), rounding=ROUND_DOWN)


async def create_listing(session: AsyncSession, user, inventory_id: int, price: Decimal, currency: str) -> Listing:
    if currency not in wallet.CURRENCIES:
        raise MarketError("Valyuta noto‘g‘ri (abu_f yoki abu_ton).")
    if price <= 0:
        raise MarketError("Narx musbat bo‘lishi kerak.")
    item = await session.get(InventoryItem, inventory_id)
    if not item or item.user_id != user.id:
        raise MarketError("Bu buyum sizda yo‘q.")
    existing = (await session.execute(select(Listing).where(Listing.inventory_id == inventory_id))).scalar_one_or_none()
    if existing and existing.status == "active":
        raise MarketError("Bu buyum allaqachon sotuvda.")
    if existing:  # bekor qilingan e'lonni qayta ochamiz
        existing.price, existing.currency, existing.status = price, currency, "active"
        existing.fee = fee_for(price)
        await session.flush()
        return existing
    listing = Listing(inventory_id=inventory_id, seller_id=user.id, currency=currency, price=price,
                      fee=fee_for(price), status="active")
    try:
        async with session.begin_nested():
            session.add(listing)
            await session.flush()
    except IntegrityError:
        raise MarketError("E’lon yaratib bo‘lmadi, qayta urinib ko‘ring.")
    return listing


async def cancel_listing(session: AsyncSession, user, listing_id: int) -> None:
    listing = await session.get(Listing, listing_id, with_for_update=True)
    if not listing or listing.seller_id != user.id:
        raise MarketError("E’lon topilmadi.")
    if listing.status != "active":
        raise MarketError("Bu e’lonni bekor qilib bo‘lmaydi.")
    listing.status = "cancelled"


async def buy(session: AsyncSession, buyer, listing_id: int) -> Listing:
    listing = await session.get(Listing, listing_id, with_for_update=True)
    if not listing or listing.status != "active":
        raise MarketError("Bu e’lon faol emas.")
    if listing.seller_id == buyer.id:
        raise MarketError("O‘zingizning e’loningizni sotib ololmaysiz.")
    item = await session.get(InventoryItem, listing.inventory_id, with_for_update=True)
    if not item or item.user_id != listing.seller_id:
        raise MarketError("Buyum endi sotuvchida emas.")
    try:
        await wallet.apply_transaction(session, user_id=buyer.id, currency=listing.currency, amount=-listing.price,
                                       kind="market_buy", note=f"Bozor: e’lon #{listing.id}",
                                       idempotency_key=f"mbuy:{listing.id}")
    except wallet.InsufficientFunds:
        raise MarketError("Balans yetarli emas.")
    payout = listing.price - listing.fee
    await wallet.apply_transaction(session, user_id=listing.seller_id, currency=listing.currency, amount=payout,
                                   kind="market_sale", note=f"Sotuv: e’lon #{listing.id}",
                                   idempotency_key=f"msale:{listing.id}")
    item.user_id = buyer.id
    listing.buyer_id = buyer.id
    listing.status = "sold"
    return listing
