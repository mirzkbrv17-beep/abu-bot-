import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base, User, UserAchievement
from app.services import rewards, wallet
from app.services.rewards import RewardError

T0 = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)


class RewardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.S = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.S() as s:
            s.add(User(id=1, tg_id=1, abu_id="ABU0000001", first_name="T"))
            await s.commit()
            await rewards.ensure_achievements(s)
            await s.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_daily_once_per_day(self):
        async with self.S() as s:
            u = await s.get(User, 1)
            await rewards.claim_daily(s, u, T0)
            await s.commit()
            with self.assertRaises(RewardError):
                await rewards.claim_daily(s, u, T0 + timedelta(hours=5))

    async def test_streak_increments_and_resets(self):
        async with self.S() as s:
            u = await s.get(User, 1)
            for day in range(3):
                await rewards.claim_daily(s, u, T0 + timedelta(days=day))
            self.assertEqual(u.streak, 3)
            await rewards.claim_daily(s, u, T0 + timedelta(days=6))
            self.assertEqual(u.streak, 1)
            await s.commit()

    async def test_reward_amount_grows_and_vip_doubles(self):
        self.assertEqual(rewards.daily_reward(1, False), Decimal("12"))
        self.assertEqual(rewards.daily_reward(1, True), Decimal("24"))
        self.assertEqual(rewards.daily_reward(999, False), Decimal("70"))  # 10 + 2*30

    async def test_seven_day_achievement_granted_once(self):
        async with self.S() as s:
            u = await s.get(User, 1)
            got = []
            for day in range(7):
                r = await rewards.claim_daily(s, u, T0 + timedelta(days=day))
                got += r["achievements"]
            await s.commit()
            self.assertTrue(any("Haftalik" in g for g in got))
            rows = (await s.execute(select(UserAchievement))).scalars().all()
            self.assertEqual(len({r.achievement_id for r in rows}), len(rows))

    async def test_vip_purchase_and_insufficient(self):
        async with self.S() as s:
            u = await s.get(User, 1)
            with self.assertRaises(RewardError):
                await rewards.buy_vip(s, u, 1, T0)
            await wallet.apply_transaction(s, user_id=1, currency="abu_f", amount=Decimal("1000"), kind="admin")
            until = await rewards.buy_vip(s, u, 1, T0)
            await s.commit()
            self.assertTrue(rewards.is_vip(u, T0))
            self.assertEqual(until, T0 + timedelta(days=30))
            self.assertEqual(await wallet.get_balance(s, 1, "abu_f"), Decimal("0"))


if __name__ == "__main__":
    unittest.main()
