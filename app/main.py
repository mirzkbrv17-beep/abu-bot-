import logging
from contextlib import asynccontextmanager

from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.admin import router as admin_router
from app.api.miniapp import router as api_router

from app.bot.setup import bot, dp
from app.config import get_settings
from app.db.session import SessionLocal, init_db
from app.services import catalog, emoji_store, rewards

logging.basicConfig(level=logging.INFO)
s = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with SessionLocal() as session:
        await emoji_store.reload(session)
        await catalog.seed_defaults(session)
        await rewards.ensure_achievements(session)
        await session.commit()
    if s.webhook_base_url:
        await bot.set_webhook(f"{s.webhook_base_url.rstrip('/')}/webhook", secret_token=s.webhook_secret,
                              allowed_updates=dp.resolve_used_update_types(), drop_pending_updates=False)
    yield
    await bot.session.close()


app = FastAPI(title="ABU BOT", lifespan=lifespan)
app.include_router(api_router)
app.include_router(admin_router)
STATIC = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/admin")
async def admin_panel():
    return FileResponse(STATIC / "admin.html", headers={"Cache-Control": "no-store"})


@app.get("/app")
async def miniapp():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    if x_telegram_bot_api_secret_token != s.webhook_secret:
        raise HTTPException(status_code=403)
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}
