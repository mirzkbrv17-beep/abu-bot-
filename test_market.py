import unittest
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, InventoryItem, Order, Product, User
from app.services import market, wallet
from app.services.market import MarketError


class MarketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.S = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.S() as s:
            s.add(User(id=1, tg_id=1, abu_id="ABU0000001", first_name="Seller"))
            s.add(User(id=2, tg_id=2, abu_id="ABU0000002", first_name="Buyer"))
            s.add(Product(id=1, sku="g", category="nft", title="G", price_currency="abu_f", price=Decimal("1")))
            s.add(Order(id=1, user_id=1, product_id=1, total=Decimal("1"), currency="abu_f", status="delivered"))
            s.add(InventoryItem(id=1, user_id=1, product_id=1, order_id=1, serial=1))
            await s.commit()
            await wallet.apply_transaction(s, user_id=2, currency="abu_f", amount=Decimal("500"), kind="admin")
            await s.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_sell_and_buy_moves_item_and_money_with_fee(self):
        async with self.S() as s:
            seller, buyer = await s.get(User, 1), await s.get(User, 2)
            l = await market.create_listing(s, seller, 1, Decimal("100"), "abu_f")
            self.assertEqual(l.fee, Decimal("5.0000"))
            await s.commit()
            await market.buy(s, buyer, l.id)
            await s.commit()
            self.assertEqual(await wallet.get_balance(s, 2, "abu_f"), Decimal("400"))
            self.assertEqual(await wallet.get_balance(s, 1, "abu_f"), Decimal("95"))
            item = await s.get(InventoryItem, 1)
            self.assertEqual(item.user_id, 2)

    async def test_cannot_buy_own_or_twice(self):
        async with self.S() as s:
            seller, buyer = await s.get(User, 1), await s.get(User, 2)
            l = await market.create_listing(s, seller, 1, Decimal("10"), "abu_f")
            await s.commit()
            with self.assertRaises(MarketError):
                await market.buy(s, seller, l.id)
            await market.buy(s, buyer, l.id)
            await s.commit()
            with self.assertRaises(MarketError):
                await market.buy(s, buyer, l.id)

    async def test_insufficient_funds_keeps_item(self):
        async with self.S() as s:
            seller, buyer = await s.get(User, 1), await s.get(User, 2)
            l = await market.create_listing(s, seller, 1, Decimal("9999"), "abu_f")
            await s.commit()
            with self.assertRaises(MarketError):
                await market.buy(s, buyer, l.id)
            await s.rollback()
            item = await s.get(InventoryItem, 1)
            self.assertEqual(item.user_id, 1)

    async def test_cancel_and_not_owner(self):
        async with self.S() as s:
            seller, buyer = await s.get(User, 1), await s.get(User, 2)
            l = await market.create_listing(s, seller, 1, Decimal("10"), "abu_f")
            await s.commit()
            with self.assertRaises(MarketError):
                await market.cancel_listing(s, buyer, l.id)
            await market.cancel_listing(s, seller, l.id)
            await s.commit()
            self.assertEqual(l.status, "cancelled")


if __name__ == "__main__":
    unittest.main()
