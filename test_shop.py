import unittest
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, InventoryItem, Product, User
from app.services import shop, wallet


class FakeBot:
    def __init__(self):
        self.refunds = []

    async def refund_star_payment(self, user_id, telegram_payment_charge_id):
        self.refunds.append(telegram_payment_charge_id)

    async def send_message(self, *a, **k):
        pass


class ShopTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.Session = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.Session() as s:
            s.add(User(tg_id=1, abu_id="ABU0000001", first_name="T"))
            s.add(Product(sku="nft1", category="nft", title="N", price_currency="abu_ton", price=Decimal("5"), stock=1))
            s.add(Product(sku="pk", category="stars_pack", title="P", price_currency="stars", price=Decimal("50"),
                          meta={"credit_currency": "abu_f", "credit_amount": 500}))
            s.add(Product(sku="bad-gift", category="gift", title="G", price_currency="stars", price=Decimal("10"), meta={}))
            await s.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _get(self, s, sku):
        return (await s.execute(select(Product).where(Product.sku == sku))).scalar_one()

    async def test_internal_purchase_gives_serial_and_decrements_stock(self):
        async with self.Session() as s:
            user = await s.get(User, 1)
            await wallet.apply_transaction(s, user_id=1, currency="abu_ton", amount=Decimal("10"), kind="admin")
            p = await self._get(s, "nft1")
            o = await shop.create_order(s, user, p)
            await shop.pay_internal(s, o, p)
            o = await shop.finalize(s, FakeBot(), o.id)
            await s.commit()
            self.assertEqual(o.status, "delivered")
            self.assertEqual(await wallet.get_balance(s, 1, "abu_ton"), Decimal("5"))
            inv = (await s.execute(select(InventoryItem))).scalars().all()
            self.assertEqual([i.serial for i in inv], [1])
            await s.refresh(p)
            self.assertEqual(p.stock, 0)

    async def test_insufficient_funds_keeps_stock(self):
        async with self.Session() as s:
            user = await s.get(User, 1)
            p = await self._get(s, "nft1")
            o = await shop.create_order(s, user, p)
            with self.assertRaises(shop.ShopError):
                await shop.pay_internal(s, o, p)
            await s.commit()
            await s.refresh(p)
            self.assertEqual(p.stock, 1)

    async def test_no_overselling(self):
        async with self.Session() as s:
            p = await self._get(s, "nft1")
            self.assertTrue(await shop.reserve_stock(s, p.id))
            self.assertFalse(await shop.reserve_stock(s, p.id))

    async def test_stars_topup_and_duplicate_payment_ignored(self):
        async with self.Session() as s:
            user = await s.get(User, 1)
            p = await self._get(s, "pk")
            o = await shop.create_order(s, user, p)
            self.assertTrue(await shop.reserve_for_stars(s, o))
            first = await shop.mark_stars_paid(s, o, "chg1", {})
            second = await shop.mark_stars_paid(s, o, "chg1", {})
            self.assertIsNotNone(first)
            self.assertIsNone(second)
            o = await shop.finalize(s, FakeBot(), o.id)
            await s.commit()
            self.assertEqual(o.status, "delivered")
            self.assertEqual(await wallet.get_balance(s, 1, "abu_f"), Decimal("500"))

    async def test_failed_delivery_refunds_stars(self):
        bot = FakeBot()
        async with self.Session() as s:
            user = await s.get(User, 1)
            p = await self._get(s, "bad-gift")  # gift_id yo'q -> yetkazib bo'lmaydi
            o = await shop.create_order(s, user, p)
            await shop.reserve_for_stars(s, o)
            await shop.mark_stars_paid(s, o, "chg2", {})
            o = await shop.finalize(s, bot, o.id)
            self.assertEqual(o.status, "refunded")
            self.assertEqual(bot.refunds, ["chg2"])


if __name__ == "__main__":
    unittest.main()
