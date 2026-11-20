import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, PromoCode, Task, User, Wallet
from app.services import promo, tasks, wallet
from app.services.promo import PromoError
from app.services.tasks import TaskError


class FakeBot:
    def __init__(self, status="member"):
        self.status = status

    async def get_chat_member(self, chat_id, tg_id):
        return SimpleNamespace(status=self.status)


class TasksPromoTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.S = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.S() as s:
            for i in (1, 2):
                s.add(User(id=i, tg_id=100 + i, abu_id=f"ABU000000{i}", first_name=f"U{i}"))
            s.add(Task(sku="daily", kind="daily", title="Kunlik", reward_amount=Decimal("10"), xp_reward=20))
            s.add(Task(sku="chan", kind="channel", title="Kanal", reward_amount=Decimal("50"), chat_id=-1, xp_reward=5))
            s.add(PromoCode(code="ABU2026", currency="abu_f", amount=Decimal("100"), max_uses=2))
            s.add(PromoCode(code="OLD", currency="abu_f", amount=Decimal("1"), expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc)))
            await s.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _user(self, s, uid=1):
        return await s.get(User, uid)

    async def test_daily_task_once_per_day_and_xp(self):
        async with self.S() as s:
            u = await self._user(s)
            task = (await s.execute(select(Task).where(Task.sku == "daily"))).scalar_one()
            xp = await tasks.complete(s, FakeBot(), u, task)
            await s.commit()
            self.assertEqual(xp, 20)
            self.assertEqual(await wallet.get_balance(s, 1, "abu_f"), Decimal("10"))
            with self.assertRaises(TaskError):
                await tasks.complete(s, FakeBot(), u, task)

    async def test_channel_task_requires_membership(self):
        async with self.S() as s:
            u = await self._user(s)
            task = (await s.execute(select(Task).where(Task.sku == "chan"))).scalar_one()
            with self.assertRaises(TaskError):
                await tasks.complete(s, FakeBot("left"), u, task)
            await tasks.complete(s, FakeBot("member"), u, task)
            await s.commit()
            self.assertEqual(await wallet.get_balance(s, 1, "abu_f"), Decimal("50"))

    async def test_promo_redeem_once_per_user(self):
        async with self.S() as s:
            u = await self._user(s)
            self.assertEqual(await promo.redeem(s, u, " abu2026 "), Decimal("100"))
            await s.commit()
            with self.assertRaises(PromoError):
                await promo.redeem(s, u, "ABU2026")

    async def test_promo_limit_enforced(self):
        async with self.S() as s:
            await promo.redeem(s, await self._user(s, 1), "ABU2026")
            await promo.redeem(s, await self._user(s, 2), "ABU2026")
            await s.commit()
            p = (await s.execute(select(PromoCode).where(PromoCode.code == "ABU2026"))).scalar_one()
            self.assertEqual(p.used_count, 2)

    async def test_promo_limit_exhausted_and_expired(self):
        async with self.S() as s:
            p = (await s.execute(select(PromoCode).where(PromoCode.code == "ABU2026"))).scalar_one()
            p.max_uses = 1
            p.used_count = 1
            await s.commit()
            with self.assertRaises(PromoError):
                await promo.redeem(s, await self._user(s), "ABU2026")
            with self.assertRaises(PromoError):
                await promo.redeem(s, await self._user(s), "OLD")
            with self.assertRaises(PromoError):
                await promo.redeem(s, await self._user(s), "NOPE")


if __name__ == "__main__":
    unittest.main()
