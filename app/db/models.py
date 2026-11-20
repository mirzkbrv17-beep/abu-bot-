from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (JSON, BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey,
                        Integer, Numeric, String, Text, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

BigPK = BigInteger().with_variant(Integer, "sqlite")


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    abu_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(128), default="")
    language: Mapped[str] = mapped_column(String(4), default="uz")
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    last_daily_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vip_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    referrer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("user_id", "currency"),
                      CheckConstraint("balance >= 0", name="ck_wallet_nonneg"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    currency: Mapped[str] = mapped_column(String(16))  # abu_f | abu_ton
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(BigPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    currency: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))  # + kirim, - chiqim
    balance_after: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    kind: Mapped[str] = mapped_column(String(32))  # referral, admin, purchase, reward, transfer...
    note: Mapped[str] = mapped_column(String(255), default="")
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    actor_tg_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EmojiMapping(Base):
    __tablename__ = "emoji_mappings"
    emoji: Mapped[str] = mapped_column(String(32), primary_key=True)
    custom_emoji_id: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(32), default="custom")
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RequiredChannel(Base):
    __tablename__ = "required_channels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(128), default="")
    invite_link: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigPK, primary_key=True)
    actor_tg_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(128), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Product(Base):
    """Do'kon katalogi: premium, stars, gift, collectible, nft, item."""
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    category: Mapped[str] = mapped_column(String(24), index=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    price_currency: Mapped[str] = mapped_column(String(16))  # abu_f | abu_ton | stars
    price: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    stock: Mapped[int | None] = mapped_column(Integer)  # None = cheksiz
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(BigPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    total: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    currency: Mapped[str] = mapped_column(String(16))
    # pending | paid | processing | delivered | failed | refunded | cancelled
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    target_tg_id: Mapped[int | None] = mapped_column(BigInteger)
    note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(BigPK, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    provider: Mapped[str] = mapped_column(String(16))  # stars | internal
    status: Mapped[str] = mapped_column(String(16), default="pending")
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    currency: Mapped[str] = mapped_column(String(16))
    telegram_charge_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InventoryItem(Base):
    """Foydalanuvchi egalik qiladigan mahsulotlar (collectible, NFT, maxsus)."""
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("product_id", "serial"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    serial: Mapped[int | None] = mapped_column(Integer)  # limitli nashr raqami (#1, #2...)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Task(Base):
    """Vazifa: daily (har kuni), once (bir marta), channel (kanalga obuna), referral."""
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(16))
    chat_id: Mapped[int | None] = mapped_column(BigInteger)  # channel vazifasi uchun
    reward_currency: Mapped[str] = mapped_column(String(16), default="abu_f")
    reward_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    xp_reward: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TaskCompletion(Base):
    __tablename__ = "task_completions"
    __table_args__ = (UniqueConstraint("user_id", "task_id", "period"),)
    id: Mapped[int] = mapped_column(BigPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    period: Mapped[str] = mapped_column(String(16))  # "once" yoki "2026-11-20"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PromoCode(Base):
    __tablename__ = "promo_codes"
    __table_args__ = (CheckConstraint("used_count >= 0", name="ck_promo_used_nonneg"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    currency: Mapped[str] = mapped_column(String(16), default="abu_f")
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    max_uses: Mapped[int | None] = mapped_column(Integer)  # None = cheksiz
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PromoRedemption(Base):
    __tablename__ = "promo_redemptions"
    __table_args__ = (UniqueConstraint("promo_id", "user_id"),)
    id: Mapped[int] = mapped_column(BigPK, primary_key=True)
    promo_id: Mapped[int] = mapped_column(ForeignKey("promo_codes.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(128))
    emoji: Mapped[str] = mapped_column(String(16), default="🏅")
    reward_abu_f: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id"),)
    id: Mapped[int] = mapped_column(BigPK, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Listing(Base):
    """Bozor e'loni. Har bir inventar buyumi uchun bitta qator; bekor qilinsa qayta ochiladi."""
    __tablename__ = "listings"
    __table_args__ = (CheckConstraint("price > 0", name="ck_listing_price_pos"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"), unique=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    currency: Mapped[str] = mapped_column(String(16))  # abu_f | abu_ton
    price: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    fee: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)  # active|sold|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
