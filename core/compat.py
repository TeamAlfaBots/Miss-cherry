# ╔══════════════════════════════════════════╗
# ║   Miss Cherry - Kurigram compat helpers  ║
# ╚══════════════════════════════════════════╝
# Kurigram / Pyrogram 2.x return ENUMS (ChatMemberStatus, MessageEntityType...)
# not plain strings.  These helpers work with both enums and strings.

import time

from pyrogram import enums

from core.config import cfg
from core.database import get_sudos

_ADMIN_NAMES = {"owner", "administrator"}


def enum_name(value) -> str:
    """ChatMemberStatus.OWNER / "creator" / "OWNER"  ->  "owner" (lowercase)."""
    if value is None:
        return ""
    name = getattr(value, "name", None) or str(value)
    name = name.split(".")[-1].lower()
    return "owner" if name == "creator" else name


def is_admin_status(status) -> bool:
    return enum_name(status) in _ADMIN_NAMES


def is_owner_status(status) -> bool:
    return enum_name(status) == "owner"


def member_status(member) -> str:
    """Status of a ChatMember that may be None (user not in chat -> 'left')."""
    if member is None:
        return "left"
    return enum_name(member.status) or "left"


ADMINS_FILTER = enums.ChatMembersFilter.ADMINISTRATORS

# ── small TTL cache so we don't call get_chat_member on every message ──
_ADMIN_CACHE: dict = {}
_TTL = 60


async def is_chat_admin(client, chat_id: int, user_id: int) -> bool:
    # bot owners / sudo users count as admins everywhere
    if user_id in cfg.OWNER_ID or user_id in await get_sudos():
        return True
    key = (chat_id, user_id)
    hit = _ADMIN_CACHE.get(key)
    now = time.time()
    if hit and now - hit[1] < _TTL:
        return hit[0]
    try:
        member = await client.get_chat_member(chat_id, user_id)
        value = is_admin_status(member.status)
    except Exception:
        value = False
    _ADMIN_CACHE[key] = (value, now)
    return value


def clear_admin_cache(chat_id: int = None):
    if chat_id is None:
        _ADMIN_CACHE.clear()
        return
    for k in [k for k in _ADMIN_CACHE if k[0] == chat_id]:
        _ADMIN_CACHE.pop(k, None)
