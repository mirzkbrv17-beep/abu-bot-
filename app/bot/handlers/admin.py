import html
import json
from decimal import Decimal, InvalidOperation

from aiogram import Bot, Router
from aiogram.filters import BaseFilter, Command, CommandObject
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.utils import send
from app.config import get_settings
from app.db.models import AuditLog, RequiredChannel
from app.services import emoji_store, users, wallet
from app.services.emoji import DEFAULT_EMOJI, emoji, valid_custom_id


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return bool(message.from_user and message.from_user.id in get_settings().admin_id_set)


router = Router()
router.message.filter(IsAdmin())


@router.message(Command("admin"))
async def admin_help(m: Message):
    await send(m, (
        "⚙️ <b>Admin buyruqlari</b>\n\n<b>Emoji sozlamalari</b>\n"
        "/emoji_categories — kategoriyalar\n/emoji_list [kategoriya] — mappinglar\n"
        "/emoji_set ❤️ 5368324170671202286 — Custom Emoji biriktirish/tahrirlash\n"
        "/emoji_remove ❤️ — mappingni o‘chirish\n/emoji_reset [kategoriya] — standartga qaytarish\n"
        "/emoji_preview 5368324170671202286 — emoji ko‘rinishi\n/emoji_test matn — to‘liq xabar sinovi\n"
        "/emoji_export — JSON eksport\n/emoji_import — JSON faylga javob sifatida yuboring\n\n"
        "<b>Kanallar</b>\n/channel_add @kanal — majburiy obuna\n/channel_remove @kanal\n/channel_list\n\n"
        "<b>Vazifa va promo</b>\n/task_add, /promo_add KOD valyuta miqdor limit|- kun|-, /promo_off KOD\n\n"
        "<b>Do‘kon</b>\n/product_list, /product_add, /product_meta, /product_toggle, /gifts_sync, /refund ID\n\n"
        "<b>Balans</b>\n/adjust TG_ID abu_f|abu_ton SUMMA izoh — balansni o‘zgartirish (audit yoziladi)"))


@router.message(Command("emoji_categories"))
async def cats(m: Message):
    names = sorted(set(DEFAULT_EMOJI.values()) | {"custom"})
    by = {c: " ".join(e for e, k in DEFAULT_EMOJI.items() if k == c) for c in names}
    await send(m, "\n".join(f"<b>{c}</b>: {by[c]}" for c in names if by[c]))


@router.message(Command("emoji_list"))
async def elist(m: Message, command: CommandObject, session: AsyncSession):
    rows = await emoji_store.list_mappings(session, (command.args or "").strip() or None)
    if not rows:
        return await send(m, "ℹ️ Mapping yo‘q. Hammasi oddiy emoji bilan chiqadi.")
    await send(m, "\n".join(f"{r.emoji} → <code>{r.custom_emoji_id}</code> ({r.category})" for r in rows))


async def _check_id(bot: Bot, cid: str) -> bool:
    if not valid_custom_id(cid):
        return False
    try:
        return bool(await bot.get_custom_emoji_stickers([cid]))  # Telegram'dan haqiqiyligini tekshiradi
    except Exception:
        return False


@router.message(Command("emoji_set"))
async def eset(m: Message, command: CommandObject, session: AsyncSession, bot: Bot):
    parts = (command.args or "").split()
    if len(parts) != 2:
        return await send(m, "ℹ️ Format: /emoji_set ❤️ 5368324170671202286")
    char, cid = parts
    if not await _check_id(bot, cid):
        return await send(m, "❌ Bu Custom Emoji ID Telegram'da topilmadi yoki noto‘g‘ri.")
    await emoji_store.set_mapping(session, char, cid, m.from_user.id)
    await send(m, f"✅ Saqlandi: {char} → <code>{cid}</code>\nYangi xabarlarda ishlaydi.")


@router.message(Command("emoji_remove"))
async def eremove(m: Message, command: CommandObject, session: AsyncSession):
    ok = await emoji_store.remove_mapping(session, command.args or "", m.from_user.id)
    await send(m, "✅ O‘chirildi." if ok else "ℹ️ Bunday mapping yo‘q.")


@router.message(Command("emoji_reset"))
async def ereset(m: Message, command: CommandObject, session: AsyncSession):
    await emoji_store.reset(session, m.from_user.id, (command.args or "").strip() or None)
    await send(m, "✅ Standart emojilar tiklandi.")


@router.message(Command("emoji_preview"))
async def epreview(m: Message, command: CommandObject, bot: Bot):
    cid = (command.args or "").strip()
    if not await _check_id(bot, cid):
        return await send(m, "❌ ID topilmadi.")
    await m.answer(f'<tg-emoji emoji-id="{cid}">⭐</tg-emoji> Ko‘rinish sinovi', parse_mode="HTML")


@router.message(Command("emoji_test"))
async def etest(m: Message, command: CommandObject):
    text = html.escape(command.args or "👤 🛍 💎 🎁 🎨 🪙 ✅ ❌ ❤️")
    await send(m, f"🔔 <b>Sinov xabari</b>\n{text}")


@router.message(Command("emoji_export"))
async def eexport(m: Message, session: AsyncSession):
    data = (await emoji_store.export_json(session)).encode()
    await m.answer_document(BufferedInputFile(data, filename="abu_emoji_config.json"))


@router.message(Command("emoji_import"))
async def eimport(m: Message, session: AsyncSession, bot: Bot):
    doc = m.reply_to_message.document if m.reply_to_message else None
    if not doc or doc.file_size > 200_000:
        return await send(m, "ℹ️ JSON faylga reply qilib /emoji_import yuboring.")
    buf = await bot.download(doc)
    try:
        n = await emoji_store.import_json(session, buf.read().decode(), m.from_user.id)
    except (ValueError, json.JSONDecodeError) as e:
        return await send(m, f"❌ Import bekor qilindi: {html.escape(str(e))}")
    await send(m, f"✅ {n} ta mapping import qilindi.")


@router.message(Command("channel_add"))
async def chadd(m: Message, command: CommandObject, session: AsyncSession, bot: Bot):
    ref = (command.args or "").strip()
    if not ref:
        return await send(m, "ℹ️ Format: /channel_add @kanal_nomi")
    try:
        chat = await bot.get_chat(ref if ref.startswith(("@", "-")) else f"@{ref}")
    except Exception:
        return await send(m, "❌ Kanal topilmadi. Bot kanalga admin sifatida qo‘shilganini tekshiring.")
    if (await session.execute(select(RequiredChannel).where(RequiredChannel.chat_id == chat.id))).scalar_one_or_none():
        return await send(m, "ℹ️ Bu kanal allaqachon qo‘shilgan.")
    session.add(RequiredChannel(chat_id=chat.id, username=chat.username, title=chat.title or ""))
    session.add(AuditLog(actor_tg_id=m.from_user.id, action="channel_add", target=str(chat.id), details={}))
    await send(m, f"✅ Majburiy obunaga qo‘shildi: {html.escape(chat.title or str(chat.id))}")


@router.message(Command("channel_remove"))
async def chremove(m: Message, command: CommandObject, session: AsyncSession):
    ref = (command.args or "").strip().lstrip("@")
    rows = (await session.execute(select(RequiredChannel))).scalars().all()
    hit = next((r for r in rows if r.username == ref or str(r.chat_id) == ref), None)
    if not hit:
        return await send(m, "ℹ️ Bunday kanal yo‘q.")
    await session.delete(hit)
    await send(m, "✅ O‘chirildi.")


@router.message(Command("channel_list"))
async def chlist(m: Message, session: AsyncSession):
    rows = (await session.execute(select(RequiredChannel))).scalars().all()
    await send(m, "\n".join(f"{r.title} (@{r.username}) id={r.chat_id}" for r in rows) or "ℹ️ Kanal yo‘q.")


@router.message(Command("adjust"))
async def adjust(m: Message, command: CommandObject, session: AsyncSession):
    parts = (command.args or "").split(maxsplit=3)
    if len(parts) < 3 or parts[1] not in wallet.CURRENCIES:
        return await send(m, "ℹ️ Format: /adjust TG_ID abu_f|abu_ton SUMMA izoh")
    try:
        tg_id, amount = int(parts[0]), Decimal(parts[2])
    except (ValueError, InvalidOperation):
        return await send(m, "❌ TG_ID yoki summa noto‘g‘ri.")
    user = await users.get_by_tg(session, tg_id)
    if not user:
        return await send(m, "❌ Foydalanuvchi topilmadi.")
    note = parts[3] if len(parts) > 3 else "Admin tuzatishi"
    try:
        tx = await wallet.apply_transaction(session, user_id=user.id, currency=parts[1], amount=amount,
                                            kind="admin", note=note, actor_tg_id=m.from_user.id)
    except wallet.InsufficientFunds:
        return await send(m, "❌ Balans manfiy bo‘lib qolardi, amal bekor qilindi.")
    session.add(AuditLog(actor_tg_id=m.from_user.id, action="adjust", target=str(tg_id),
                         details={"currency": parts[1], "amount": str(amount), "note": note, "tx": tx.id}))
    await send(m, f"✅ Bajarildi. Yangi balans: <b>{tx.balance_after}</b>")


# ---------- Do'kon boshqaruvi ----------
from app.db.models import Product  # noqa: E402
from app.services import shop as shop_service  # noqa: E402


@router.message(Command("product_list"))
async def plist(m: Message, session: AsyncSession):
    rows = (await session.execute(select(Product).order_by(Product.category, Product.id))).scalars().all()
    await send(m, "\n".join(
        f"{'🟢' if p.is_active else '⚪'} <code>{p.sku}</code> [{p.category}] {html.escape(p.title)} — "
        f"{p.price} {p.price_currency}, qoldiq: {'∞' if p.stock is None else p.stock}, meta={p.meta}" for p in rows) or "—")


@router.message(Command("product_add"))
async def padd(m: Message, command: CommandObject, session: AsyncSession):
    parts = (command.args or "").split(maxsplit=5)
    if len(parts) < 6:
        return await send(m, "ℹ️ /product_add sku kategoriya valyuta narx qoldiq|- Sarlavha\n"
                             f"Kategoriya: {', '.join(shop_service.CATEGORIES)}; valyuta: abu_f, abu_ton, stars")
    sku, cat, cur, price, stock, title = parts
    try:
        price_d = Decimal(price)
        stock_v = None if stock == "-" else int(stock)
    except (InvalidOperation, ValueError):
        return await send(m, "❌ Narx yoki qoldiq noto‘g‘ri.")
    if cat not in shop_service.CATEGORIES or cur not in shop_service.CURRENCY_NAMES or price_d <= 0:
        return await send(m, "❌ Kategoriya, valyuta yoki narx noto‘g‘ri.")
    if (await session.execute(select(Product).where(Product.sku == sku))).scalar_one_or_none():
        return await send(m, "❌ Bu sku band.")
    session.add(Product(sku=sku, category=cat, price_currency=cur, price=price_d, stock=stock_v, title=title))
    session.add(AuditLog(actor_tg_id=m.from_user.id, action="product_add", target=sku, details={}))
    await send(m, "✅ Mahsulot qo‘shildi. Gift/Premium uchun /product_meta bilan sozlang.")


@router.message(Command("product_meta"))
async def pmeta(m: Message, command: CommandObject, session: AsyncSession):
    parts = (command.args or "").split(maxsplit=2)
    if len(parts) != 3:
        return await send(m, "ℹ️ /product_meta sku kalit qiymat  (masalan: gift_id, months, star_cost, credit_amount)")
    p = (await session.execute(select(Product).where(Product.sku == parts[0]))).scalar_one_or_none()
    if not p:
        return await send(m, "❌ Mahsulot topilmadi.")
    val = int(parts[2]) if parts[2].isdigit() and parts[1] != "gift_id" else parts[2]
    p.meta = {**(p.meta or {}), parts[1]: val}
    session.add(AuditLog(actor_tg_id=m.from_user.id, action="product_meta", target=p.sku, details={parts[1]: str(val)}))
    await send(m, "✅ Saqlandi.")


@router.message(Command("product_toggle"))
async def ptoggle(m: Message, command: CommandObject, session: AsyncSession):
    p = (await session.execute(select(Product).where(Product.sku == (command.args or "").strip()))).scalar_one_or_none()
    if not p:
        return await send(m, "❌ Mahsulot topilmadi.")
    p.is_active = not p.is_active
    await send(m, "🟢 Yoqildi." if p.is_active else "⚪ O‘chirildi.")


@router.message(Command("gifts_sync"))
async def gifts_sync(m: Message, bot: Bot):
    try:
        gifts = (await bot.get_available_gifts()).gifts
    except Exception as e:
        return await send(m, f"❌ Sovg‘alar ro‘yxatini olib bo‘lmadi: {html.escape(str(e))}")
    await send(m, "🎁 <b>Telegram sovg‘alari</b> (id — Stars narxi):\n" +
               "\n".join(f"<code>{g.id}</code> — {g.star_count}⭐" for g in gifts[:40]) +
               "\n\nMahsulot yaratib, /product_meta sku gift_id ID bilan bog‘lang.")


@router.message(Command("refund"))
async def refund(m: Message, command: CommandObject, session: AsyncSession, bot: Bot):
    if not (command.args or "").strip().isdigit():
        return await send(m, "ℹ️ /refund BUYURTMA_ID")
    session.add(AuditLog(actor_tg_id=m.from_user.id, action="refund", target=command.args.strip(), details={}))
    await send(m, html.escape(await shop_service.admin_refund(session, bot, int(command.args.strip()))))


# ---------- Vazifa va promo boshqaruvi ----------
from app.db.models import PromoCode, Task  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

from app.services import promo as promo_service  # noqa: E402


@router.message(Command("task_add"))
async def task_add(m: Message, command: CommandObject, session: AsyncSession):
    # /task_add sku tur mukofot valyuta xp chat_id|- sarlavha
    parts = (command.args or "").split(maxsplit=6)
    if len(parts) < 7:
        return await send(m, "ℹ️ /task_add sku tur(daily|once|channel|referral) mukofot valyuta(abu_f|abu_ton) xp chat_id|- Sarlavha")
    sku, kind, amt, cur, xp, chat, title = parts
    try:
        amount = Decimal(amt)
        xp_v = int(xp)
        chat_id = None if chat == "-" else int(chat)
    except (InvalidOperation, ValueError):
        return await send(m, "❌ Raqam yoki chat_id noto‘g‘ri.")
    if kind not in ("daily", "once", "channel", "referral") or cur not in ("abu_f", "abu_ton") or amount <= 0:
        return await send(m, "❌ Tur, valyuta yoki mukofot noto‘g‘ri.")
    if kind == "channel" and not chat_id:
        return await send(m, "❌ Kanal vazifasi uchun chat_id kerak.")
    session.add(Task(sku=sku, kind=kind, reward_amount=amount, reward_currency=cur, xp_reward=xp_v,
                     chat_id=chat_id, title=title))
    session.add(AuditLog(actor_tg_id=m.from_user.id, action="task_add", target=sku, details={}))
    await send(m, "✅ Vazifa qo‘shildi.")


@router.message(Command("promo_add"))
async def promo_add(m: Message, command: CommandObject, session: AsyncSession):
    # /promo_add KOD valyuta miqdor max_uses|- kun|-
    parts = (command.args or "").split()
    if len(parts) != 5:
        return await send(m, "ℹ️ /promo_add KOD valyuta(abu_f|abu_ton) miqdor limit|- muddat_kun|-")
    code, cur, amt, lim, days = parts
    code = promo_service.normalize(code)
    try:
        amount = Decimal(amt)
        max_uses = None if lim == "-" else int(lim)
        expires = None if days == "-" else datetime.now(timezone.utc) + timedelta(days=int(days))
    except (InvalidOperation, ValueError):
        return await send(m, "❌ Raqam noto‘g‘ri.")
    if cur not in ("abu_f", "abu_ton") or amount <= 0 or (max_uses is not None and max_uses < 1):
        return await send(m, "❌ Valyuta, miqdor yoki limit noto‘g‘ri.")
    if (await session.execute(select(PromoCode).where(PromoCode.code == code))).scalar_one_or_none():
        return await send(m, "❌ Bu kod band.")
    session.add(PromoCode(code=code, currency=cur, amount=amount, max_uses=max_uses, expires_at=expires))
    session.add(AuditLog(actor_tg_id=m.from_user.id, action="promo_add", target=code, details={}))
    await send(m, f"✅ Promo-kod yaratildi: <code>{code}</code>")


@router.message(Command("promo_off"))
async def promo_off(m: Message, command: CommandObject, session: AsyncSession):
    code = promo_service.normalize(command.args or "")
    p = (await session.execute(select(PromoCode).where(PromoCode.code == code))).scalar_one_or_none()
    if not p:
        return await send(m, "❌ Topilmadi.")
    p.is_active = False
    session.add(AuditLog(actor_tg_id=m.from_user.id, action="promo_off", target=code, details={}))
    await send(m, "⚪ Promo-kod o‘chirildi.")
