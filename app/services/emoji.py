"""Markazlashgan emoji renderer. Hech qanday tashqi kutubxonaga bog'liq emas.

Barcha bot matnlari shu orqali o'tadi: oddiy emoji -> <tg-emoji emoji-id="..">emoji</tg-emoji>.
"""
import re
import time

VS16 = "\ufe0f"
ID_RE = re.compile(r"^[0-9]{6,20}$")
_TOKEN = re.compile(r"(<tg-emoji\b[^>]*>.*?</tg-emoji>|<[^>]*>)", re.S)

# emoji -> kategoriya (admin ko'rishi uchun)
DEFAULT_EMOJI: dict[str, str] = {
    "👤": "menu", "🛍": "menu", "💎": "currency", "🎁": "gifts", "🎨": "nft",
    "📋": "tasks", "🎟": "promo", "👥": "referral", "🏆": "level", "⚙": "menu", "❓": "menu",
    "🪙": "currency", "⭐": "payment", "👑": "vip", "🔥": "streak", "📈": "level",
    "✅": "success", "❌": "error", "⚠": "error", "ℹ": "general", "❤": "general",
    "🌟": "achievement", "🏅": "achievement", "🎉": "success", "💳": "payment",
    "📦": "order", "🔔": "notification", "🌐": "settings", "🔗": "referral",
    "▰": "level", "▱": "level", "🆔": "profile", "🇺🇿": "settings", "🇷🇺": "settings", "🇬🇧": "settings",
}


def norm(e: str) -> str:
    return e.replace(VS16, "")


def valid_custom_id(value: str) -> bool:
    return bool(ID_RE.match(value or ""))


class EmojiRenderer:
    def __init__(self, ttl: int = 30):
        self._map: dict[str, str] = {}
        self._pattern: re.Pattern | None = None
        self._loaded_at = 0.0
        self.ttl = ttl

    def set_mappings(self, mapping: dict[str, str]) -> None:
        clean = {norm(k): v for k, v in mapping.items() if valid_custom_id(v)}
        self._map = clean
        keys = sorted(clean, key=len, reverse=True)
        self._pattern = re.compile("|".join(re.escape(k) + VS16 + "?" for k in keys)) if keys else None
        self._loaded_at = time.monotonic()

    def is_stale(self) -> bool:
        return time.monotonic() - self._loaded_at > self.ttl

    @property
    def mappings(self) -> dict[str, str]:
        return dict(self._map)

    def render(self, text: str, use_custom: bool = True) -> str:
        """Telegram HTML matnidagi oddiy emojilarni Custom Emoji bilan almashtiradi.
        Teglar ichiga va tayyor <tg-emoji> ichiga tegmaydi."""
        if not use_custom or not self._pattern:
            return text
        parts = _TOKEN.split(text)
        for i in range(0, len(parts), 2):  # juft indekslar = oddiy matn
            parts[i] = self._pattern.sub(self._sub, parts[i])
        return "".join(parts)

    def _sub(self, m: re.Match) -> str:
        cid = self._map[norm(m.group(0))]
        return f'<tg-emoji emoji-id="{cid}">{m.group(0)}</tg-emoji>'


emoji = EmojiRenderer()
