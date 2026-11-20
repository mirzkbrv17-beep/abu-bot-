import html

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.utils import fmt, send
from app.db.models import InventoryItem, Listing, Product
from app.services import market
from app.services.market import MarketError

router = Router()
CUR = {"abu_f": "ABU F", "abu_ton": "ABU TON"}


@router.message(Command("market"))
async def browse(m: Message, session: AsyncSession, db_user):
    if not db_user:
        return await send(m, "ℹ️ Avval /start buyrug‘ini yuboring.")
    rows = (await session.execute(select(Listing, InventoryItem, Product)
            .join(InventoryItem, InventoryItem.id == Listing.inventory_id)
            .join(Product, Product.id == InventoryItem.product_id)
            .where(Listing.status == "active").order_by(Listing.id.desc()).limit(20))).all()
    if not rows:
        return await send(m, "🛒 <b>Bozor</b>\n\nHozircha faol e’lonlar yo‘q.\n\nSotish: <code>/sell BUYUM_ID NARX abu_f|abu_ton</code>")
    lines = [f"#{l.id} <b>{html.escape(p.title)}</b>"
             f"{' #' + str(i.serial) if i.serial else ''} — {fmt(l.price)} {CUR[l.currency]}" for l, i, p in rows]
    await send(m, "🛒 <b>Bozor</b>\n\n" + "\n".join(lines) + "\n\nSotib olish: <code>/buy E’LON_ID</code>")


@router.message(Command("sell"))
async def sell(m: Message, command: CommandObject, session: AsyncSession, db_user):
    if not db_user:
        return await send(m, "ℹ️ Avval /start buyrug‘ini yuboring.")
    parts = (command.args or "").split()
    if len(parts) != 3 or not parts[0].isdigit():
        return await send(m, "ℹ️ Format: <code>/sell BUYUM_ID NARX abu_f|abu_ton</code>\nBuyum ID larini /orders orqali ko‘ring.")
    try:
        from decimal import Decimal, InvalidOperation
        price = Decimal(parts[1])
    except InvalidOperation:
        return await send(m, "❌ Narx noto‘g‘ri.")
    try:
        listing = await market.create_listing(session, db_user, int(parts[0]), price, parts[2])
    except MarketError as e:
        return await send(m, f"❌ {html.escape(str(e))}")
    await send(m, f"✅ E’lon #{listing.id} joylandi. Komissiya: {fmt(listing.fee)} {CUR[listing.currency]}")


@router.message(Command("buy"))
async def buy(m: Message, command: CommandObject, session: AsyncSession, db_user):
    if not db_user:
        return await send(m, "ℹ️ Avval /start buyrug‘ini yuboring.")
    if not (command.args or "").strip().isdigit():
        return await send(m, "ℹ️ Format: <code>/buy E’LON_ID</code>")
    try:
        listing = await market.buy(session, db_user, int(command.args.strip()))
    except MarketError as e:
        return await send(m, f"❌ {html.escape(str(e))}")
    await send(m, f"🎉 Sotib olindi: e’lon #{listing.id} — {fmt(listing.price)} {CUR[listing.currency]}")


@router.message(Command("cancel_listing"))
async def cancel(m: Message, command: CommandObject, session: AsyncSession, db_user):
    if not db_user:
        return await send(m, "ℹ️ Avval /start buyrug‘ini yuboring.")
    if not (command.args or "").strip().isdigit():
        return await send(m, "ℹ️ Format: <code>/cancel_listing E’LON_ID</code>")
    try:
        await market.cancel_listing(session, db_user, int(command.args.strip()))
    except MarketError as e:
        return await send(m, f"❌ {html.escape(str(e))}")
    await send(m, "⚪ E’lon bekor qilindi.")
