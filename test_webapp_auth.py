import hashlib
import hmac
import json
import unittest
from urllib.parse import urlencode

from app.services.webapp_auth import InvalidInitData, verify_init_data

TOKEN = "123:TEST"


def make_init(token=TOKEN, auth_date=1_700_000_000, user_id=42, tamper=False):
    fields = {"auth_date": str(auth_date), "user": json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if tamper:
        fields["user"] = json.dumps({"id": 999}, separators=(",", ":"))
    return urlencode({**fields, "hash": h})


class WebAppAuthTests(unittest.TestCase):
    def test_valid(self):
        u = verify_init_data(make_init(), TOKEN, now=1_700_000_100)
        self.assertEqual(u["id"], 42)

    def test_wrong_token(self):
        with self.assertRaises(InvalidInitData):
            verify_init_data(make_init(), "other:TOKEN", now=1_700_000_100)

    def test_tampered_user_rejected(self):
        with self.assertRaises(InvalidInitData):
            verify_init_data(make_init(tamper=True), TOKEN, now=1_700_000_100)

    def test_expired(self):
        with self.assertRaises(InvalidInitData):
            verify_init_data(make_init(), TOKEN, now=1_700_000_000 + 90_000)

    def test_missing_hash_and_empty(self):
        with self.assertRaises(InvalidInitData):
            verify_init_data("", TOKEN)
        with self.assertRaises(InvalidInitData):
            verify_init_data("auth_date=1&user=%7B%7D", TOKEN, now=1)


if __name__ == "__main__":
    unittest.main()
