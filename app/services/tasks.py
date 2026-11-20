from datetime import datetime, timezone
from decimal import Decimal

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Task, TaskCompletion, User
from app.services import wallet

LEVEL_XP = 100  # har 100 XP = 1 daraja (2-bosqichdagi qoida bilan mos)


class TaskError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato."""


def period_for(task: Task, now: datetime | None = None) -> str:
    if task.kind == "daily":
        return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    return "once"


async def list_tasks(session: AsyncSession, user: User) -> list[tuple[Task, bool]]:
    tasks = (await session.execute(select(Task).where(Task.is_active.is_(True)).order_by(Task.id))).scalars().all()
    out = []
    for t in tasks:
        done = (await session.execute(select(TaskCompletion.id).where(
            TaskCompletion.user_id == user.id, TaskCompletion.task_id == t.id,
            TaskCompletion.period == period_for(t)))).first() is not None
        out.append((t, done))
    return out


async def _check_channel(bot: Bot, task: Task, tg_id: int) -> None:
    if task.kind != "channel" or not task.chat_id:
        return
    try:
        m = await bot.get_chat_member(task.chat_id, tg_id)
    except Exception:
        raise TaskError("Kanalni tekshirib bo‘lmadi. Keyinroq urinib ko‘ring.")
    if m.status not in ("member", "administrator", "creator"):
        raise TaskError("Avval kanalga obuna bo‘ling.")


async def complete(session: AsyncSession, bot: Bot, user: User, task: Task) -> int:
    """Vazifani bajarilgan deb belgilaydi va mukofotni beradi. Qaytaradi: berilgan XP.
    Bir davrda (kuniga yoki bir marta) qayta bajarib bo‘lmaydi."""
    if not task.is_active:
        raise TaskError("Bu vazifa faol emas.")
    if task.kind == "referral":
        from app.services.users import referral_count
        if await referral_count(session, user.id) < 1:
            raise TaskError("Avval kamida bitta do‘st taklif qiling.")
    await _check_channel(bot, task, user.tg_id)
    period = period_for(task)
    try:
        async with session.begin_nested():
            session.add(TaskCompletion(user_id=user.id, task_id=task.id, period=period))
            await session.flush()
    except IntegrityError:
        raise TaskError("Bu vazifa allaqachon bajarilgan.")
    await wallet.apply_transaction(session, user_id=user.id, currency=task.reward_currency,
                                   amount=Decimal(task.reward_amount), kind="task",
                                   note=f"Vazifa: {task.title}",
                                   idempotency_key=f"task:{task.id}:{user.id}:{period}")
    user.xp += task.xp_reward
    user.level = user.xp // LEVEL_XP + 1
    return task.xp_reward
