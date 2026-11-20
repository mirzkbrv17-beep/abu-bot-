import logging

from aiogram import Router
from aiogram.types import ErrorEvent

from app.bot.texts import t

log = logging.getLogger(__name__)
router = Router()


@router.errors()
async def on_error(event: ErrorEvent):
    log.exception("Xatolik: %s", event.exception)
    msg = event.update.message or (event.update.callback_query.message if event.update.callback_query else None)
    if msg:
        try:
            await msg.answer(t("uz", "error"))  # foydalanuvchiga texnik xato ko'rsatilmaydi
        except Exception:
            pass
    return True
