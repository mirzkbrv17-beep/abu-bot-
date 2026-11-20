import html

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.texts import LANGS, t
from app.bot.utils import main_menu, send
from app.services import users
from app.services.subscription import missing_channels

router = Router()


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=v, callback_data=f"lang:{k}")]
                                                  for k, v in LANGS.items()])


async def proceed(bot: Bot, msg: Message, session: AsyncSession, user, first: bool = False):
    """Obunani tekshiradi; hammasi joyida bo'lsa menyuni ko'rsatadi."""
    missing = await missing_channels(bot, session, user.tg_id)
    if missing:
        rows = []
        for ch in missing:
            url = ch.invite_link or (f"https://t.me/{ch.username}" if ch.username else None)
            if url:
                rows.append([InlineKeyboardButton(text=ch.title or ch.username or "Kanal", url=url)])
        rows.append([InlineKeyboardButton(text=t(user.language, "check_sub"), callback_data="checksub")])
        await send(msg, t(user.language, "must_sub"), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        return
    key = "welcome" if first else "welcome_back"
    await send(msg, t(user.language, key, name=html.escape(user.first_name), abu_id=user.abu_id),
               reply_markup=main_menu(user.language))


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, session: AsyncSession, bot: Bot):
    ref = None
    if command.args and command.args.startswith("ref_") and command.args[4:].isdigit():
        ref = int(command.args[4:])
    user, created = await users.get_or_create(session, message.from_user, ref)
    if created:
        await send(message, t("uz", "choose_lang"), reply_markup=lang_kb())
    else:
        await proceed(bot, message, session, user)


@router.callback_query(F.data.startswith("lang:"))
async def pick_lang(cb: CallbackQuery, session: AsyncSession, db_user, bot: Bot):
    lang = cb.data.split(":", 1)[1]
    if not db_user or lang not in LANGS:
        return await cb.answer()
    db_user.language = lang
    await cb.answer(t(lang, "lang_set"))
    await proceed(bot, cb.message, session, db_user, first=True)


@router.callback_query(F.data == "checksub")
async def check_sub(cb: CallbackQuery, session: AsyncSession, db_user, bot: Bot):
    if not db_user:
        return await cb.answer()
    if await missing_channels(bot, session, db_user.tg_id):
        return await cb.answer(t(db_user.language, "still_missing"), show_alert=True)
    await cb.answer()
    await proceed(bot, cb.message, session, db_user)
