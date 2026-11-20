"""Veb admin panel API. Har bir so'rov ADMIN_PANEL_TOKEN bilan tekshiriladi.
Har bir o'zgarish audit jurnaliga yoziladi."""
import hmac
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.config import get_settings
from app.db.models import AuditLog, EmojiMapping, Product, PromoCode, Task, Transaction, User
from app.db.session import SessionLocal
from app.services import emoji_store, promo, wallet
from app.services.emoji import valid_custom_id

router = APIRouter(prefix="/admin/api", tags=["admin"])
ACTOR = 0  # veb paneldan qilingan amallar uchun audit identifikatori


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = get_settings().admin_panel_token
    if not expected or len(expected) < 24:
        raise HTTPException(503, "ADMIN_PANEL_TOKEN sozlanmagan (kamida 24 belgi)")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(401, "ruxsat yo'q")


def audit(s, action: str, target: str, details: dict | None = None) -> None:
    s.add(AuditLog(actor_tg_id=ACTOR, action=f"web:{action}", target=target[:128], details=details or {}))


def _d(v) -> str:
    return f"{v:f}" if v is not None else None


# ---------- Foydalanuvchilar ----------
@router.get("/users", dependencies=[Depends(require_admin)])
async def users_list(q: str = "", limit: int = 50, offset: int = 0):
    limit = max(1, min(limit, 200))
    async with SessionLocal() as s:
        stmt = select(User).order_by(User.id.desc())
        if q.strip():
            like = f"%{q.strip()}%"
            stmt = stmt.where(or_(User.abu_id.ilike(like), User.username.ilike(like),
                                  User.first_name.ilike(like), User.tg_id.cast(str_type()).ilike(like)))
        rows = (await s.execute(stmt.limit(limit).offset(offset))).scalars().all()
        total = (await s.execute(select(func.count(User.id)))).scalar_one()
        return {"total": total, "items": [
            {"id": u.id, "tg_id": u.tg_id, "abu_id": u.abu_id, "name": u.first_name, "username": u.username,
             "level": u.level, "xp": u.xp, "streak": u.streak, "banned": u.is_banned} for u in rows]}


def str_type():
    from sqlalchemy import String
    return String


class BanIn(BaseModel):
    banned: bool


@router.post("/users/{user_id}/ban", dependencies=[Depends(require_admin)])
async def ban(user_id: int, body: BanIn):
    async with SessionLocal() as s:
        u = await s.get(User, user_id)
        if not u:
            raise HTTPException(404, "topilmadi")
        u.is_banned = body.banned
        audit(s, "ban" if body.banned else "unban", str(u.tg_id))
        await s.commit()
        return {"ok": True, "banned": u.is_banned}


class AdjustIn(BaseModel):
    currency: str
    amount: str = Field(..., description="Musbat yoki manfiy raqam, masalan 50 yoki -20")
    note: str = Field("Admin tuzatishi", max_length=200)


@router.post("/users/{user_id}/adjust", dependencies=[Depends(require_admin)])
async def adjust(user_id: int, body: AdjustIn):
    try:
        amt = Decimal(body.amount)
    except InvalidOperation:
        raise HTTPException(400, "summa noto'g'ri")
    async with SessionLocal() as s:
        u = await s.get(User, user_id)
        if not u:
            raise HTTPException(404, "topilmadi")
        try:
            tx = await wallet.apply_transaction(s, user_id=u.id, currency=body.currency, amount=amt,
                                                kind="admin", note=body.note)
        except wallet.InsufficientFunds:
            raise HTTPException(409, "balans manfiy bo'lib qoladi")
        except ValueError as e:
            raise HTTPException(400, str(e))
        audit(s, "adjust", str(u.tg_id), {"currency": body.currency, "amount": body.amount, "tx": tx.id})
        await s.commit()
        return {"ok": True, "balance_after": _d(tx.balance_after)}


@router.get("/users/{user_id}/transactions", dependencies=[Depends(require_admin)])
async def user_tx(user_id: int):
    async with SessionLocal() as s:
        rows = (await s.execute(select(Transaction).where(Transaction.user_id == user_id)
                                .order_by(Transaction.id.desc()).limit(100))).scalars().all()
        return {"items": [{"id": t.id, "currency": t.currency, "amount": _d(t.amount), "kind": t.kind,
                           "note": t.note, "at": t.created_at.isoformat()} for t in rows]}


# ---------- Do'kon, promo, vazifa ----------
@router.get("/products", dependencies=[Depends(require_admin)])
async def products():
    async with SessionLocal() as s:
        rows = (await s.execute(select(Product).order_by(Product.id))).scalars().all()
        return {"items": [{"id": p.id, "sku": p.sku, "title": p.title, "category": p.category,
                           "price": _d(p.price), "currency": p.price_currency, "stock": p.stock,
                           "active": p.is_active} for p in rows]}


@router.post("/products/{pid}/toggle", dependencies=[Depends(require_admin)])
async def toggle_product(pid: int):
    async with SessionLocal() as s:
        p = await s.get(Product, pid)
        if not p:
            raise HTTPException(404, "topilmadi")
        p.is_active = not p.is_active
        audit(s, "product_toggle", p.sku, {"active": p.is_active})
        await s.commit()
        return {"active": p.is_active}


@router.get("/promos", dependencies=[Depends(require_admin)])
async def promos():
    async with SessionLocal() as s:
        rows = (await s.execute(select(PromoCode).order_by(PromoCode.id.desc()))).scalars().all()
        return {"items": [{"id": p.id, "code": p.code, "amount": _d(p.amount), "currency": p.currency,
                           "used": p.used_count, "max_uses": p.max_uses, "active": p.is_active,
                           "expires_at": p.expires_at.isoformat() if p.expires_at else None} for p in rows]}


class PromoIn(BaseModel):
    code: str = Field(..., min_length=3, max_length=32)
    currency: str
    amount: str
    max_uses: int | None = None
    days: int | None = None


@router.post("/promos", dependencies=[Depends(require_admin)])
async def create_promo(body: PromoIn):
    code = promo.normalize(body.code)
    try:
        amount = Decimal(body.amount)
    except InvalidOperation:
        raise HTTPException(400, "miqdor noto'g'ri")
    if body.currency not in wallet.CURRENCIES or amount <= 0 or (body.max_uses is not None and body.max_uses < 1):
        raise HTTPException(400, "ma'lumot noto'g'ri")
    async with SessionLocal() as s:
        if (await s.execute(select(PromoCode).where(PromoCode.code == code))).scalar_one_or_none():
            raise HTTPException(409, "kod band")
        exp = datetime.now(timezone.utc) + timedelta(days=body.days) if body.days else None
        s.add(PromoCode(code=code, currency=body.currency, amount=amount, max_uses=body.max_uses, expires_at=exp))
        audit(s, "promo_create", code)
        await s.commit()
    return {"ok": True, "code": code}


@router.post("/promos/{code}/off", dependencies=[Depends(require_admin)])
async def promo_off(code: str):
    async with SessionLocal() as s:
        p = (await s.execute(select(PromoCode).where(PromoCode.code == promo.normalize(code)))).scalar_one_or_none()
        if not p:
            raise HTTPException(404, "topilmadi")
        p.is_active = False
        audit(s, "promo_off", p.code)
        await s.commit()
    return {"ok": True}


@router.get("/tasks", dependencies=[Depends(require_admin)])
async def tasks_list():
    async with SessionLocal() as s:
        rows = (await s.execute(select(Task).order_by(Task.id))).scalars().all()
        return {"items": [{"id": t.id, "sku": t.sku, "title": t.title, "kind": t.kind, "reward": _d(t.reward_amount),
                           "currency": t.reward_currency, "xp": t.xp_reward, "active": t.is_active} for t in rows]}


# ---------- Emoji ----------
@router.get("/emoji", dependencies=[Depends(require_admin)])
async def emoji_list():
    async with SessionLocal() as s:
        rows = await emoji_store.list_mappings(s)
        return {"items": [{"emoji": r.emoji, "custom_emoji_id": r.custom_emoji_id, "category": r.category} for r in rows]}


class EmojiIn(BaseModel):
    emoji: str = Field(..., max_length=16)
    custom_emoji_id: str


@router.post("/emoji", dependencies=[Depends(require_admin)])
async def emoji_set(body: EmojiIn):
    if not valid_custom_id(body.custom_emoji_id):
        raise HTTPException(400, "Custom Emoji ID noto'g'ri")
    async with SessionLocal() as s:
        try:
            await emoji_store.set_mapping(s, body.emoji, body.custom_emoji_id, ACTOR)
        except ValueError as e:
            raise HTTPException(400, str(e))
        await s.commit()
    return {"ok": True}


@router.delete("/emoji/{char}", dependencies=[Depends(require_admin)])
async def emoji_del(char: str):
    async with SessionLocal() as s:
        ok = await emoji_store.remove_mapping(s, char, ACTOR)
        await s.commit()
    return {"ok": ok}


# ---------- Audit ----------
@router.get("/audit", dependencies=[Depends(require_admin)])
async def audit_list(limit: int = 100):
    async with SessionLocal() as s:
        rows = (await s.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500)))).scalars().all()
        return {"items": [{"id": a.id, "actor": a.actor_tg_id, "action": a.action, "target": a.target,
                           "details": a.details, "at": a.created_at.isoformat()} for a in rows]}
