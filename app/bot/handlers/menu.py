import html
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.start import lang_kb
from app.bot.texts import LANGS, menu_labels, t
from app.bot.utils import fmt, main_menu, progress_bar, send
from app.config import get_settings
from app.services import users, wallet

router = Router()


def _need_user(db_user) -> bool:
    return db_user is None


@router.message(F.text.in_(menu_labels("cabinet")))
async def cabinet(m: Message, session: AsyncSession, db_user):
    if _need_user(db_user):
        return await send(m, t("uz", "start_first"))
    lang = db_user.language
    abu_f = await wallet.get_balance(session, db_user.id, "abu_f")
    abu_ton = await wallet.get_balance(session, db_user.id, "abu_ton")
    refs = await users.referral_count(session, db_user.id)
    vip = t(lang, "vip_no")
    until = db_user.vip_until
    if until is not None:
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        if until > datetime.now(timezone.utc):
            vip = t(lang, "vip_yes", until=until.strftime("%Y-%m-%d"))
    await send(m, t(lang, "cabinet", name=html.escape(db_user.first_name),
                    username=f"@{html.escape(db_user.username)}" if db_user.username else "",
                    abu_id=db_user.abu_id, abu_f=fmt(abu_f), abu_ton=fmt(abu_ton), vip=vip,
                    level=db_user.level, bar=progress_bar(db_user.xp), xp=db_user.xp,
                    streak=db_user.streak, refs=refs))


@router.message(F.text.in_(menu_labels("currencies")))
async def currencies(m: Message, session: AsyncSession, db_user):
    if _need_user(db_user):
        return await send(m, t("uz", "start_first"))
    lang = db_user.language
    abu_f = await wallet.get_balance(session, db_user.id, "abu_f")
    abu_ton = await wallet.get_balance(session, db_user.id, "abu_ton")
    txs = await wallet.history(session, db_user.id, 10)
    names = {"abu_f": "ABU F", "abu_ton": "ABU TON"}
    lines = [f"{'+' if x.amount > 0 else ''}{fmt(x.amount)} {names[x.currency]} — {html.escape(x.note or x.kind)}"
             for x in txs]
    await send(m, t(lang, "currencies", abu_f=fmt(abu_f), abu_ton=fmt(abu_ton),
                    tx="\n".join(lines) if lines else t(lang, "no_tx")))


@router.message(F.text.in_(menu_labels("referrals")))
async def referrals(m: Message, session: AsyncSession, db_user):
    if _need_user(db_user):
        return await send(m, t("uz", "start_first"))
    s = get_settings()
    me = (s.bot_username or (await m.bot.me()).username)
    link = f"https://t.me/{me}?start=ref_{db_user.tg_id}"
    await send(m, t(db_user.language, "referrals", count=await users.referral_count(session, db_user.id),
                    bonus=fmt(s.referral_bonus_abu_f), link=link))


@router.message(F.text.in_(menu_labels("rating")))
async def rating(m: Message, session: AsyncSession, db_user):
    if _need_user(db_user):
        return await send(m, t("uz", "start_first"))
    top = await users.top_by_xp(session, 10)
    rows = "\n".join(f"{i}. {html.escape(u.first_name)} — {u.xp} XP (🆔 {u.abu_id})" for i, u in enumerate(top, 1))
    await send(m, t(db_user.language, "rating", rows=rows or "—"))


@router.message(F.text.in_(menu_labels("settings")))
async def settings(m: Message, db_user):
    if _need_user(db_user):
        return await send(m, t("uz", "start_first"))
    await send(m, t(db_user.language, "settings"), reply_markup=lang_kb())


@router.message(F.text.in_(menu_labels("help")))
async def help_(m: Message, db_user):
    await send(m, t(db_user.language if db_user else "uz", "help"))


