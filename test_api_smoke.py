"""Ilova import bo'lishi va asosiy marshrutlar ro'yxatdan o'tganini tekshiradi (ma'lumotlar bazasiz)."""
import os
import unittest

os.environ.setdefault("BOT_TOKEN", "123:TEST")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


class ApiSmokeTests(unittest.TestCase):
    def test_routes_registered(self):
        from app.main import app
        paths = {r.path for r in app.routes}
        for p in ("/health", "/webhook", "/api/me", "/api/banners", "/app", "/admin",
                  "/admin/api/users", "/admin/api/audit"):
            self.assertIn(p, paths)

    def test_health_endpoint(self):
        try:
            from fastapi.testclient import TestClient
        except Exception:
            self.skipTest("httpx o'rnatilmagan")
        from app.main import app
        with TestClient(app) as c:  # lifespan: webhook o'rnatilmaydi (WEBHOOK_BASE_URL bo'sh)
            self.assertEqual(c.get("/health").json(), {"status": "ok"})

    def test_admin_requires_token(self):
        try:
            from fastapi.testclient import TestClient
        except Exception:
            self.skipTest("httpx o'rnatilmagan")
        from app.main import app
        with TestClient(app) as c:
            self.assertIn(c.get("/admin/api/users").status_code, (401, 503))


if __name__ == "__main__":
    unittest.main()
