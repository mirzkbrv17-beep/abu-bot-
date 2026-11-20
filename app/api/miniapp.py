from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select

from app.config import get_settings
from app.db.models import InventoryItem, Order, Product, Transaction, User
from app.db.session import SessionLocal
from app.services import users, wallet
from app.services.webapp_auth import InvalidInitData, verify_init_data

router = APIRouter(prefix="/api")


async def current_user(authorization: str | None = Header(default=None)) -> User:
    """Authorization: tma <initData>. Foydalanuvchi faqat o'zining ma'lumotini ko'radi."""
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(401, "auth kerak")
    try:
        tg = verify_init_data(authorization[4:], get_settings().bot_token)
    except InvalidInitData:
        raise HTTPException(401, "auth noto'g'ri")
    async with SessionLocal() as s:
        user = await users.get_by_tg(s, int(tg["id"]))
    if not user or user.is_banned:
        raise HTTPException(403, "ruxsat yo'q")
    return user


def _dec(d: Decimal) -> str:
    return f"{d:f}"


@router.get("/me")
async def me(user: User = Depends(current_user)):
    async with SessionLocal() as s:
        abu_f = await wallet.get_balance(s, user.id, "abu_f")
        abu_ton = await wallet.get_balance(s, user.id, "abu_ton")
        refs = await users.referral_count(s, user.id)
        txs = await wallet.history(s, user.id, 10)
        orders = (await s.execute(select(Order, Product).join(Product, Product.id == Order.product_id)
                                  .where(Order.user_id == user.id).order_by(Order.id.desc()).limit(10))).all()
        inv = (await s.execute(select(InventoryItem, Product).join(Product, Product.id == InventoryItem.product_id)
                               .where(InventoryItem.user_id == user.id).order_by(InventoryItem.id.desc()))).all()
    vip = bool(user.vip_until and user.vip_until.replace(tzinfo=user.vip_until.tzinfo or timezone.utc)
               > datetime.now(timezone.utc))
    return {
        "abu_id": user.abu_id, "name": user.first_name, "username": user.username,
        "balances": {"abu_f": _dec(abu_f), "abu_ton": _dec(abu_ton)},
        "vip": vip, "level": user.level, "xp": user.xp, "xp_in_level": user.xp % 100,
        "streak": user.streak, "referrals": refs,
        "transactions": [{"currency": t.currency, "amount": _dec(t.amount), "note": t.note or t.kind,
                          "at": t.created_at.isoformat()} for t in txs],
        "orders": [{"id": o.id, "title": p.title, "status": o.status} for o, p in orders],
        "collection": [{"title": p.title, "serial": i.serial} for i, p in inv],
    }


@router.get("/banners")
async def banners():
    # Admin keyinchalik banner boshqaruvini qo'shadi; hozircha tayyor kontent.
    return {"items": [
        {"title": "ABU F bilan do‘kon", "subtitle": "Tangalaringizni premium mahsulotga almashtiring", "tone": "gold"},
        {"title": "Referal bonusi", "subtitle": "Do‘st taklif qiling, ABU F oling", "tone": "aurora"},
        {"title": "Kolleksiya", "subtitle": "Limitli NFT nashrlari", "tone": "violet"},
    ]}
