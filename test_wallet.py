"""Pytest/unittest. Ishga tushirish: pip install -r requirements.txt && python -m unittest discover tests"""
import unittest
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, User
from app.services import wallet


class WalletTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.Session = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.Session() as s:
            s.add(User(tg_id=1, abu_id="ABU0000001", first_name="T"))
            await s.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_credit_debit_and_history(self):
        async with self.Session() as s:
            await wallet.apply_transaction(s, user_id=1, currency="abu_f", amount=Decimal("100"), kind="admin")
            await wallet.apply_transaction(s, user_id=1, currency="abu_f", amount=Decimal("-30"), kind="purchase")
            await s.commit()
            self.assertEqual(await wallet.get_balance(s, 1, "abu_f"), Decimal("70"))
            self.assertEqual(len(await wallet.history(s, 1)), 2)

    async def test_no_negative_balance(self):
        async with self.Session() as s:
            with self.assertRaises(wallet.InsufficientFunds):
                await wallet.apply_transaction(s, user_id=1, currency="abu_ton", amount=Decimal("-1"), kind="purchase")

    async def test_idempotency(self):
        async with self.Session() as s:
            a = await wallet.apply_transaction(s, user_id=1, currency="abu_f", amount=Decimal("5"), kind="reward", idempotency_key="k1")
            b = await wallet.apply_transaction(s, user_id=1, currency="abu_f", amount=Decimal("5"), kind="reward", idempotency_key="k1")
            await s.commit()
            self.assertEqual(a.id, b.id)
            self.assertEqual(await wallet.get_balance(s, 1, "abu_f"), Decimal("5"))

    async def test_unknown_currency_and_zero(self):
        async with self.Session() as s:
            with self.assertRaises(ValueError):
                await wallet.apply_transaction(s, user_id=1, currency="usd", amount=Decimal("1"), kind="x")
            with self.assertRaises(ValueError):
                await wallet.apply_transaction(s, user_id=1, currency="abu_f", amount=Decimal("0"), kind="x")


if __name__ == "__main__":
    unittest.main()
