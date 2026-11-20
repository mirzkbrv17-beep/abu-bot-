import html

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.texts import menu_labels, t
from app.bot.utils import fmt, send
from app.db.models import Task
from app.services import promo, tasks
from app.services.promo import PromoError
from app.services.tasks import TaskError

router = Router()


def _cur(c: str) -> str:
    return {"abu_f": "ABU F", "abu_ton": "ABU TON"}.get(c, c)


@router.message(F.text.in_(menu_labels("tasks")))
async def tasks_menu(m: Message, session: AsyncSession, db_user):
    if not db_user:
        return await send(m, t("uz", "start_first"))
    rows = await tasks.list_tasks(session, db_user)
    if not rows:
        return await send(m, "📋 Hozircha vazifalar yo‘q.")
    lines, kb = [], []
    for task, done in rows:
        mark = "✅" if done else "⬜"
        lines.append(f"{mark} <b>{html.escape(task.title)}</b> — +{fmt(task.reward_amount)} {_cur(task.reward_currency)}, +{task.xp_reward} XP")
        if not done:
            kb.append([InlineKeyboardButton(text=f"Bajardim: {task.title[:28]}", callback_data=f"task:{task.id}")])
    await send(m, "📋 <b>Vazifalar</b>\n\n" + "\n".join(lines) + "\n\nKunlik vazifalar har kuni yangilanadi.",
               reply_markup=InlineKeyboardMarkup(inline_keyboard=kb) if kb else None)


@router.callback_query(F.data.startswith("task:"))
async def task_done(cb: CallbackQuery, session: AsyncSession, db_user, bot: Bot):
    if not db_user:
        return await cb.answer()
    task = await session.get(Task, int(cb.data.split(":")[1]))
    if not task:
        return await cb.answer("Vazifa topilmadi", show_alert=True)
    try:
        xp = await tasks.complete(session, bot, db_user, task)
    except TaskError as e:
        return await cb.answer(str(e), show_alert=True)
    await cb.answer("✅ Bajarildi!")
    await send(cb.message, f"🎉 <b>{html.escape(task.title)}</b> bajarildi: "
                           f"+{fmt(task.reward_amount)} {_cur(task.reward_currency)}, +{xp} XP")


@router.message(F.text.in_(menu_labels("promo")))
async def promo_hint(m: Message, db_user):
    if not db_user:
        return await send(m, t("uz", "start_first"))
    await send(m, "🎟 Promo-kodni shunday yuboring:\n<code>/promo KOD</code>")


@router.message(Command("promo"))
async def promo_redeem(m: Message, command: CommandObject, session: AsyncSession, db_user):
    if not db_user:
        return await send(m, t("uz", "start_first"))
    try:
        amount = await promo.redeem(session, db_user, command.args or "")
    except PromoError as e:
        return await send(m, f"❌ {html.escape(str(e))}")
    await send(m, f"🎉 Promo-kod qabul qilindi: +{fmt(amount)} ABU F")
