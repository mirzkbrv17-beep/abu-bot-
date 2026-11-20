import html

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message,
                           PreCheckoutQuery)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.texts import menu_labels, t
from app.bot.utils import fmt, send
from app.db.models import InventoryItem, Order, Product
from app.services import shop

router = Router()
CAT_TITLES = {"premium": "👑 Telegram Premium", "stars_pack": "⭐ Stars bilan to‘ldirish",
              "gift": "🎁 Telegram sovg‘alari", "collectible": "🏅 Collectible",
              "nft": "🎨 NFT", "item": "🛍 Maxsus mahsulotlar"}


def _kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _price(p: Product) -> str:
    return f"{fmt(p.price)} {shop.CURRENCY_NAMES[p.price_currency]}"


async def _categories(m: Message, cats: list[str], title_key: str):
    rows = [[InlineKeyboardButton(text=CAT_TITLES[c], callback_data=f"cat:{c}")] for c in cats]
    await send(m, t("uz", title_key), reply_markup=_kb(rows))


@router.message(F.text.in_(menu_labels("shop")))
async def shop_home(m: Message, db_user):
    if not db_user:
        return await send(m, t("uz", "start_first"))
    await _categories(m, ["premium", "stars_pack", "gift", "collectible", "nft", "item"], "shop_home")


@router.message(F.text.in_(menu_labels("gifts")))
async def gifts_home(m: Message, db_user):
    if not db_user:
        return await send(m, t("uz", "start_first"))
    await _categories(m, ["gift", "premium"], "gifts_home")


@router.message(F.text.in_(menu_labels("nft")))
async def nft_home(m: Message, db_user):
    if not db_user:
        return await send(m, t("uz", "start_first"))
    await _categories(m, ["nft", "collectible"], "nft_home")


@router.callback_query(F.data.startswith("cat:"))
async def show_category(cb: CallbackQuery, session: AsyncSession):
    cat = cb.data.split(":", 1)[1]
    products = await shop.list_products(session, cat)
    await cb.answer()
    if not products:
        return await send(cb.message, "ℹ️ Bu bo‘limda hozircha mahsulot yo‘q.")
    rows = [[InlineKeyboardButton(text=f"{p.title} — {_price(p)}", callback_data=f"prod:{p.id}")] for p in products]
    await send(cb.message, f"<b>{CAT_TITLES.get(cat, cat)}</b>", reply_markup=_kb(rows))


@router.callback_query(F.data.startswith("prod:"))
async def show_product(cb: CallbackQuery, session: AsyncSession):
    p = await session.get(Product, int(cb.data.split(":")[1]))
    await cb.answer()
    if not p or not p.is_active:
        return await send(cb.message, "❌ Mahsulot topilmadi.")
    stock = "cheksiz" if p.stock is None else str(p.stock)
    extra = "\n🎁 Sovg‘a sizning o‘zingizga yuboriladi." if p.category in ("gift", "premium") else ""
    await send(cb.message, f"<b>{html.escape(p.title)}</b>\n{html.escape(p.description)}\n\n"
                           f"💳 Narx: <b>{_price(p)}</b>\n📦 Qoldiq: {stock}{extra}",
               reply_markup=_kb([[InlineKeyboardButton(text="✅ Sotib olish", callback_data=f"buy:{p.id}")]]))


@router.callback_query(F.data.startswith("buy:"))
async def buy(cb: CallbackQuery, session: AsyncSession, db_user):
    p = await session.get(Product, int(cb.data.split(":")[1]))
    await cb.answer()
    if not db_user or not p:
        return
    try:
        order = await shop.create_order(session, db_user, p)
    except shop.ShopError as e:
        return await send(cb.message, f"❌ {e}")
    if p.price_currency == "stars":
        await cb.message.answer_invoice(title=p.title[:32], description=(p.description or p.title)[:255],
                                        payload=f"order:{order.id}", currency="XTR",
                                        prices=[LabeledPrice(label=p.title[:32], amount=int(p.price))])
    else:
        await send(cb.message, f"🛍 <b>{html.escape(p.title)}</b>\nTo‘lov: <b>{_price(p)}</b>",
                   reply_markup=_kb([[InlineKeyboardButton(text="💳 To‘lash", callback_data=f"pay:{order.id}")]]))


@router.callback_query(F.data.startswith("pay:"))
async def pay(cb: CallbackQuery, session: AsyncSession, db_user, bot: Bot):
    order = await session.get(Order, int(cb.data.split(":")[1]))
    await cb.answer()
    if not order or not db_user or order.user_id != db_user.id:
        return
    product = await session.get(Product, order.product_id)
    try:
        await shop.pay_internal(session, order, product)
    except shop.ShopError as e:
        return await send(cb.message, f"❌ {e}")
    order = await shop.finalize(session, bot, order.id)
    await _report(cb.message, order, product)


async def _report(msg: Message, order: Order, product: Product):
    if order.status == "delivered":
        await send(msg, f"🎉 Buyurtma #{order.id} bajarildi: <b>{html.escape(product.title)}</b>")
    else:
        await send(msg, f"⚠️ Buyurtma #{order.id} bajarilmadi ({html.escape(order.note)}). "
                        f"Holat: <b>{order.status}</b>. To‘lov qaytarildi.")


@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery, session: AsyncSession):
    ok, err = False, "Buyurtma topilmadi"
    if q.invoice_payload.startswith("order:") and q.invoice_payload[6:].isdigit():
        order = await session.get(Order, int(q.invoice_payload[6:]))
        if order and q.currency == "XTR" and q.total_amount == int(order.total):
            if await shop.reserve_for_stars(session, order):
                ok = True
            else:
                err = "Mahsulot tugagan yoki buyurtma eskirgan"
    await q.answer(ok=ok, error_message=None if ok else err)


@router.message(F.successful_payment)
async def paid(m: Message, session: AsyncSession, bot: Bot):
    sp = m.successful_payment
    order = await session.get(Order, int(sp.invoice_payload.split(":")[1]))
    if not order:
        return
    pay_row = await shop.mark_stars_paid(session, order, sp.telegram_payment_charge_id,
                                         {"total_amount": sp.total_amount, "currency": sp.currency})
    if pay_row is None:
        return  # takroriy xabar
    order = await shop.finalize(session, bot, order.id)
    await _report(m, order, await session.get(Product, order.product_id))


@router.message(Command("orders"))
async def my_orders(m: Message, session: AsyncSession, db_user):
    if not db_user:
        return await send(m, t("uz", "start_first"))
    rows = (await session.execute(select(Order, Product).join(Product, Product.id == Order.product_id)
                                  .where(Order.user_id == db_user.id).order_by(Order.id.desc()).limit(10))).all()
    inv = (await session.execute(select(InventoryItem, Product).join(Product, Product.id == InventoryItem.product_id)
                                 .where(InventoryItem.user_id == db_user.id).order_by(InventoryItem.id.desc()))).all()
    o = "\n".join(f"#{x.id} {html.escape(p.title)} — {x.status}" for x, p in rows) or "—"
    c = "\n".join(f"{html.escape(p.title)}" + (f" #{i.serial}" if i.serial else "") for i, p in inv) or "—"
    await send(m, f"📦 <b>Buyurtmalar</b>\n{o}\n\n🏅 <b>Kolleksiyam</b>\n{c}")
