import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api import admin

TOKEN = "x" * 30


class AdminAuthTests(unittest.TestCase):
    def test_rejects_when_token_not_configured(self):
        with patch.object(admin, "get_settings", lambda: type("S", (), {"admin_panel_token": ""})()):
            with self.assertRaises(HTTPException) as c:
                admin.require_admin("anything")
            self.assertEqual(c.exception.status_code, 503)

    def test_rejects_wrong_and_missing_token(self):
        with patch.object(admin, "get_settings", lambda: type("S", (), {"admin_panel_token": TOKEN})()):
            for bad in (None, "", "wrong", TOKEN + "x"):
                with self.assertRaises(HTTPException) as c:
                    admin.require_admin(bad)
                self.assertEqual(c.exception.status_code, 401)

    def test_accepts_correct_token(self):
        with patch.object(admin, "get_settings", lambda: type("S", (), {"admin_panel_token": TOKEN})()):
            self.assertIsNone(admin.require_admin(TOKEN))


if __name__ == "__main__":
    unittest.main()
