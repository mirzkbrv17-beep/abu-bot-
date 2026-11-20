from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import InventoryItem
from app.services import wallet


class FulfillmentError(Exception):
    pass


async def _add_inventory(session, order, product) -> None:
    for _ in range(5):
        try:
            async with session.begin_nested():
                last = (await session.execute(select(func.max(InventoryItem.serial)).where(
                    InventoryItem.product_id == product.id))).scalar() or 0
                session.add(InventoryItem(user_id=order.user_id, product_id=product.id,
                                          order_id=order.id, serial=last + 1))
                await session.flush()
            return
        except IntegrityError:
            continue
    raise FulfillmentError("Seriya raqamini berib bo‘lmadi")


async def deliver(session, bot, order, product, user) -> None:
    cat, meta = product.category, (product.meta or {})
    if cat == "stars_pack":
        cur, amt = meta.get("credit_currency", "abu_f"), Decimal(str(meta.get("credit_amount", 0)))
        if cur not in wallet.CURRENCIES or amt <= 0:
            raise FulfillmentError("Mahsulot sozlamasi noto‘g‘ri")
        await wallet.apply_transaction(session, user_id=user.id, currency=cur, amount=amt, kind="stars_topup",
                                       note=f"Stars to‘ldirish #{order.id}", idempotency_key=f"topup:{order.id}")
    elif cat in ("item", "collectible", "nft"):
        await _add_inventory(session, order, product)
    elif cat == "gift":
        gift_id = meta.get("gift_id")
        if not gift_id:
            raise FulfillmentError("Sovg‘a uchun gift_id sozlanmagan")
        try:
            await bot.send_gift(user_id=order.target_tg_id or user.tg_id, gift_id=str(gift_id))
        except Exception as e:
            raise FulfillmentError(f"Telegram sovg‘ani yubormadi: {e}")
    elif cat == "premium":
        months, cost = meta.get("months"), meta.get("star_cost")
        method = getattr(bot, "gift_premium_subscription", None)
        if not months or not cost:
            raise FulfillmentError("Premium sozlamasi (months, star_cost) to‘liq emas")
        if method is None:
            raise FulfillmentError("aiogram versiyasi Premium sovg‘ani qo‘llamaydi — yangilang")
        try:
            await method(user_id=order.target_tg_id or user.tg_id, month_count=int(months), star_count=int(cost))
        except Exception as e:
            raise FulfillmentError(f"Telegram Premium yubormadi: {e}")
    else:
        raise FulfillmentError("Noma‘lum mahsulot turi")
