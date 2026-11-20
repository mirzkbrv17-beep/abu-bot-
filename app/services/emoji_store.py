import json
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, EmojiMapping
from app.services.emoji import DEFAULT_EMOJI, emoji, norm, valid_custom_id


async def reload(session: AsyncSession) -> None:
    rows = (await session.execute(select(EmojiMapping))).scalars().all()
    emoji.set_mappings({r.emoji: r.custom_emoji_id for r in rows})


async def list_mappings(session: AsyncSession, category: str | None = None) -> list[EmojiMapping]:
    q = select(EmojiMapping).order_by(EmojiMapping.category, EmojiMapping.emoji)
    if category:
        q = q.where(EmojiMapping.category == category)
    return list((await session.execute(q)).scalars().all())


async def set_mapping(session: AsyncSession, char: str, custom_id: str, actor: int) -> None:
    char = norm(char.strip())
    if not char or len(char) > 16:
        raise ValueError("Emoji noto'g'ri")
    if not valid_custom_id(custom_id):
        raise ValueError("Custom Emoji ID noto'g'ri (faqat raqamlar bo'lishi kerak)")
    row = await session.get(EmojiMapping, char)
    cat = DEFAULT_EMOJI.get(char, "custom")
    if row:
        row.custom_emoji_id, row.updated_by = custom_id, actor
        row.updated_at = datetime.now(timezone.utc)
    else:
        session.add(EmojiMapping(emoji=char, custom_emoji_id=custom_id, category=cat, updated_by=actor))
    session.add(AuditLog(actor_tg_id=actor, action="emoji_set", target=char, details={"id": custom_id}))
    await session.flush()
    await reload(session)


async def remove_mapping(session: AsyncSession, char: str, actor: int) -> bool:
    char = norm(char.strip())
    row = await session.get(EmojiMapping, char)
    if not row:
        return False
    await session.delete(row)
    session.add(AuditLog(actor_tg_id=actor, action="emoji_remove", target=char, details={}))
    await session.flush()
    await reload(session)
    return True


async def reset(session: AsyncSession, actor: int, category: str | None = None) -> None:
    q = delete(EmojiMapping)
    if category:
        q = q.where(EmojiMapping.category == category)
    await session.execute(q)
    session.add(AuditLog(actor_tg_id=actor, action="emoji_reset", target=category or "all", details={}))
    await session.flush()
    await reload(session)


async def export_json(session: AsyncSession) -> str:
    rows = await list_mappings(session)
    return json.dumps({r.emoji: r.custom_emoji_id for r in rows}, ensure_ascii=False, indent=2)


async def import_json(session: AsyncSession, raw: str, actor: int) -> int:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON obyekt bo'lishi kerak")
    for k, v in data.items():  # avval hammasini tekshiramiz, keyin yozamiz
        if not valid_custom_id(str(v)):
            raise ValueError(f"{k}: ID noto'g'ri")
    for k, v in data.items():
        await set_mapping(session, k, str(v), actor)
    return len(data)
