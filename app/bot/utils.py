import logging
from decimal import Decimal

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from app.bot.texts import MENU_LAYOUT, t
from app.services.emoji import emoji

log = logging.getLogger(__name__)


async def send(target: Message, text: str, **kw):
    """Barcha matnlar shu yerdan o'tadi: Custom Emoji + xavfsiz fallback."""
    try:
        return await target.answer(emoji.render(text), parse_mode="HTML", **kw)
    except TelegramBadRequest as e:
        log.warning("Custom emoji bilan yuborib bo'lmadi, oddiy emoji bilan qayta uriniladi: %s", e)
        return await target.answer(emoji.render(text, use_custom=False), parse_mode="HTML", **kw)


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=t(lang, f"menu.{k}")) for k in row] for row in MENU_LAYOUT]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def fmt(amount: Decimal) -> str:
    return f"{amount.normalize():f}" if amount != amount.to_integral() else f"{int(amount):,}".replace(",", " ")


def progress_bar(xp: int, width: int = 10) -> str:
    filled = min(width, (xp % 100) * width // 100)
    return "▰" * filled + "▱" * (width - filled)
