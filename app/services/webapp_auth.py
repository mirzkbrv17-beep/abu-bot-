"""Telegram Mini App initData imzosini tekshiradi.
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
Mijoz yuborgan balans yoki ID ga ishonilmaydi: faqat imzosi to'g'ri bo'lgan initData qabul qilinadi."""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

MAX_AGE_SECONDS = 24 * 3600


class InvalidInitData(Exception):
    pass


def verify_init_data(init_data: str, bot_token: str, max_age: int = MAX_AGE_SECONDS, now: int | None = None) -> dict:
    if not init_data:
        raise InvalidInitData("initData bo'sh")
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InvalidInitData("hash yo'q")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InvalidInitData("imzo noto'g'ri")
    auth_date = int(pairs.get("auth_date", "0") or 0)
    current = int(now if now is not None else time.time())
    if auth_date <= 0 or current - auth_date > max_age:
        raise InvalidInitData("initData muddati o'tgan")
    user = json.loads(pairs.get("user", "{}") or "{}")
    if not isinstance(user, dict) or "id" not in user:
        raise InvalidInitData("foydalanuvchi ma'lumoti yo'q")
    return user
