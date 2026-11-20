import html

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.utils import fmt, send
from app.db.models import Achievement, UserAchievement
from app.services import rewards
from app.services.rewards import RewardError

router = Router()


@router.message(Command("daily"))
async def daily(m: Message, session: AsyncSession, db_user):
    if not db_user:
        return await send(m, "ℹ️ Avval /start buyrug‘ini yuboring.")
    try:
        r = await rewards.claim_daily(session, db_user)
    except RewardError as e:
        return await send(m, f"⏳ {html.escape(str(e))}")
    vip = " 👑 VIP x2" if r["vip"] else ""
    text = (f"🎁 Kunlik bonus: <b>+{fmt(r['amount'])} ABU F</b>{vip}\n🔥 Streak: <b>{r['streak']} kun</b>")
    if r["achievements"]:
        text += "\n\n🏅 Yangi yutuq:\n" + "\n".join(html.escape(a) for a in r["achievements"])
    await send(m, text)


@router.message(Command("vip"))
async def vip(m: Message, command: CommandObject, session: AsyncSession, db_user):
    if not db_user:
        return await send(m, "ℹ️ Avval /start buyrug‘ini yuboring.")
    arg = (command.args or "").strip()
    if not arg.isdigit():
        vip_on = rewards.is_vip(db_user)
        status = "faol" if vip_on else "yo‘q"
        return await send(m, f"👑 <b>VIP</b>: {status}\n"
                              "• Kunlik bonus 2 barobar\n• Narxi: 1 oy 1000, 3 oy -10%, 12 oy -20% ABU F\n\n"
                              "Sotib olish: <code>/vip 1</code>, <code>/vip 3</code> yoki <code>/vip 12</code>")
    try:
        until = await rewards.buy_vip(session, db_user, int(arg))
    except RewardError as e:
        return await send(m, f"❌ {html.escape(str(e))}")
    await send(m, f"👑 VIP faollashtirildi. Muddati: <b>{until:%Y-%m-%d}</b> gacha.")


@router.message(Command("achievements"))
async def achievements(m: Message, session: AsyncSession, db_user):
    if not db_user:
        return await send(m, "ℹ️ Avval /start buyrug‘ini yuboring.")
    await rewards.ensure_achievements(session)
    allach = (await session.execute(select(Achievement).order_by(Achievement.id))).scalars().all()
    got = set((await session.execute(select(UserAchievement.achievement_id).where(
        UserAchievement.user_id == db_user.id))).scalars().all())
    lines = [f"{a.emoji} <b>{html.escape(a.title)}</b> {'✅' if a.id in got else '🔒'}" for a in allach]
    await send(m, "🏅 <b>Yutuqlar</b>\n\n" + "\n".join(lines))
