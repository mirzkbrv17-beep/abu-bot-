import logging
from decimal import Decimal

from sqlalchemy import case, null, select, update

from app.config import get_settings
from app.db.models import Order, Payment, Product, User
from app.services import fulfillment, wallet

log = logging.getLogger(__name__)
CATEGORIES = ("premium", "stars_pack", "gift", "collectible", "nft", "item")
CURRENCY_NAMES = {"abu_f": "ABU F", "abu_ton": "ABU TON", "stars": "⭐ Stars"}


class ShopError(Exception):
    """Foydalanuvchiga ko'rsatsa bo'ladigan xato."""


async def reserve_stock(session, product_id: int, qty: int = 1) -> bool:
    """Ombor sonini atomik kamaytiradi (oshib sotilishdan himoya). stock=None cheksiz."""
    stmt = (update(Product)
            .where(Product.id == product_id, Product.is_active.is_(True),
                   Product.stock.is_(None) | (Product.stock >= qty))
            .values(stock=case((Product.stock.is_(None), null()), else_=Product.stock - qty))
            .execution_options(synchronize_session=False))
    return (await session.execute(stmt)).rowcount == 1


async def release_stock(session, product_id: int, qty: int = 1) -> None:
    stmt = (update(Product).where(Product.id == product_id)
            .values(stock=case((Product.stock.is_(None), null()), else_=Product.stock + qty))
            .execution_options(synchronize_session=False))
    await session.execute(stmt)


async def list_products(session, category: str) -> list[Product]:
    q = select(Product).where(Product.category == category, Product.is_active.is_(True),
                              Product.stock.is_(None) | (Product.stock > 0)).order_by(Product.id)
    return list((await session.execute(q)).scalars().all())


async def create_order(session, user: User, product: Product, qty: int = 1) -> Order:
    if not product.is_active or (product.stock is not None and product.stock < qty):
        raise ShopError("Mahsulot mavjud emas")
    o = Order(user_id=user.id, product_id=product.id, quantity=qty, total=product.price * qty,
              currency=product.price_currency, status="pending", target_tg_id=user.tg_id)
    session.add(o)
    await session.flush()
    return o


async def pay_internal(session, order: Order, product: Product) -> None:
    """ABU F / ABU TON bilan to'lov: ombor + balans bitta atomik blokda."""
    if order.status != "pending":
        raise ShopError("Buyurtma holati noto‘g‘ri")
    if order.currency not in wallet.CURRENCIES:
        raise ShopError("Bu mahsulot Stars bilan sotiladi")
    try:
        async with session.begin_nested():
            if not await reserve_stock(session, product.id, order.quantity):
                raise ShopError("Mahsulot tugagan")
            await wallet.apply_transaction(session, user_id=order.user_id, currency=order.currency,
                                           amount=-order.total, kind="purchase", note=f"Buyurtma #{order.id}",
                                           idempotency_key=f"order:{order.id}")
    except wallet.InsufficientFunds:
        raise ShopError("Balans yetarli emas")
    session.add(Payment(order_id=order.id, provider="internal", status="paid",
                        amount=order.total, currency=order.currency))
    order.status = "paid"


async def reserve_for_stars(session, order: Order) -> bool:
    """pre_checkout paytida ombor band qilinadi."""
    if order.status != "pending":
        return False
    if not await reserve_stock(session, order.product_id, order.quantity):
        return False
    order.status = "reserved"
    return True


async def mark_stars_paid(session, order: Order, charge_id: str, raw: dict) -> Payment | None:
    """Telegram charge_id bo'yicha takrorlanmaydi: ikkinchi marta None qaytaradi."""
    dup = (await session.execute(select(Payment).where(Payment.telegram_charge_id == charge_id))).scalar_one_or_none()
    if dup:
        return None
    if order.status != "reserved" and not await reserve_stock(session, order.product_id, order.quantity):
        order.note = "stock_missing"
    pay = Payment(order_id=order.id, provider="stars", status="paid", amount=order.total, currency="XTR",
                  telegram_charge_id=charge_id, raw=raw)
    session.add(pay)
    order.status = "paid"
    await session.flush()
    return pay


async def _notify_admins(bot, text: str) -> None:
    for admin in get_settings().admin_id_set:
        try:
            await bot.send_message(admin, text)
        except Exception:
            pass


async def finalize(session, bot, order_id: int) -> Order:
    """To'langan buyurtmani yetkazadi. Xato bo'lsa: ombor qaytadi va pul qaytariladi."""
    order = await session.get(Order, order_id)
    if order is None or order.status != "paid":
        return order
    product, user = await session.get(Product, order.product_id), await session.get(User, order.user_id)
    order.status = "processing"
    try:
        if order.note == "stock_missing":
            raise fulfillment.FulfillmentError("Mahsulot tugab qolgan")
        await fulfillment.deliver(session, bot, order, product, user)
        order.status = "delivered"
    except Exception as e:
        log.exception("Yetkazib bo'lmadi, buyurtma #%s", order.id)
        reason = str(e) if isinstance(e, fulfillment.FulfillmentError) else "Texnik xatolik"
        stock_taken = order.note != "stock_missing"
        order.note = reason[:255]
        await _fail_and_refund(session, bot, order, stock_taken)
    return order


async def _fail_and_refund(session, bot, order: Order, stock_taken: bool) -> None:
    if stock_taken:
        await release_stock(session, order.product_id, order.quantity)
    pay = (await session.execute(select(Payment).where(Payment.order_id == order.id,
                                                       Payment.status == "paid"))).scalars().first()
    if pay is None:
        order.status = "failed"
        return
    if pay.provider == "internal":
        await wallet.apply_transaction(session, user_id=order.user_id, currency=order.currency, amount=order.total,
                                       kind="refund", note=f"Qaytarildi #{order.id}",
                                       idempotency_key=f"refund:{order.id}")
        pay.status, order.status = "refunded", "refunded"
    else:
        user = await session.get(User, order.user_id)
        try:
            await bot.refund_star_payment(user_id=user.tg_id, telegram_payment_charge_id=pay.telegram_charge_id)
            pay.status, order.status = "refunded", "refunded"
        except Exception as e:
            order.status = "failed"
            await _notify_admins(bot, f"⚠️ Buyurtma #{order.id}: Stars qaytarilmadi, qo‘lda /refund {order.id} qiling. {e}")


async def admin_refund(session, bot, order_id: int) -> str:
    order = await session.get(Order, order_id)
    if not order:
        return "Buyurtma topilmadi"
    pay = (await session.execute(select(Payment).where(Payment.order_id == order.id,
                                                       Payment.status == "paid"))).scalars().first()
    if not pay or order.status in ("refunded", "cancelled"):
        return "Qaytariladigan to‘lov yo‘q"
    await _fail_and_refund(session, bot, order, stock_taken=order.note != "stock_missing")
    return f"Buyurtma #{order.id} holati: {order.status}"
