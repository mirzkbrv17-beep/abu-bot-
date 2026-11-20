from decimal import Decimal

from sqlalchemy import func, select

from app.db.models import Product

# Boshlang'ich narxlar — admin /product_add, /product_toggle orqali o'zgartiradi.
DEFAULTS = [
    dict(sku="stars-50", category="stars_pack", title="50 ⭐ → 500 ABU F", price_currency="stars", price=50,
         meta={"credit_currency": "abu_f", "credit_amount": 500}),
    dict(sku="stars-100", category="stars_pack", title="100 ⭐ → 1 100 ABU F", price_currency="stars", price=100,
         meta={"credit_currency": "abu_f", "credit_amount": 1100}),
    dict(sku="stars-250", category="stars_pack", title="250 ⭐ → 3 000 ABU F", price_currency="stars", price=250,
         meta={"credit_currency": "abu_f", "credit_amount": 3000}),
    dict(sku="premium-3m", category="premium", title="Telegram Premium — 3 oy", price_currency="stars", price=1100,
         meta={"months": 3, "star_cost": 1000}),
    dict(sku="premium-6m", category="premium", title="Telegram Premium — 6 oy", price_currency="stars", price=1650,
         meta={"months": 6, "star_cost": 1500}),
    dict(sku="premium-12m", category="premium", title="Telegram Premium — 12 oy", price_currency="stars", price=2750,
         meta={"months": 12, "star_cost": 2500}),
    dict(sku="abu-gold-badge", category="collectible", title="ABU Oltin nishon", price_currency="abu_f", price=500,
         description="Kolleksiya nishoni. Kabinetingizda saqlanadi."),
    dict(sku="abu-genesis", category="nft", title="ABU Genesis NFT", price_currency="abu_ton", price=5, stock=100,
         description="Limitli nashr (100 dona). Har biriga o‘z seriya raqami beriladi."),
]


async def seed_defaults(session) -> None:
    if (await session.execute(select(func.count(Product.id)))).scalar_one() > 0:
        return
    for d in DEFAULTS:
        session.add(Product(**{**d, "price": Decimal(str(d["price"])), "stock": d.get("stock"),
                               "description": d.get("description", "")}))
    await session.commit()
