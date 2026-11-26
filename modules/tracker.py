# ╔══════════════════════════════════════════╗
# ║      Miss Cherry - Tracker Module        ║
# ║  Saves every chat / user the bot sees    ║
# ╚══════════════════════════════════════════╝
#
# Before this module, chats were only saved on /start, so /broadcast,
# /getlink and /list missed most groups.  Now every group / channel the
# bot sees (or is added to) is stored, and chats the bot was removed
# from are marked inactive (their settings are kept).
#
# Writes are throttled in memory, so this adds ~0 DB load per message.

import time

from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated

from core.compat import enum_name, member_status
from core.database import save_chat, save_user, set_chat_active
from core.logger import logger

_CHAT_TTL = 600     # re-save a chat at most every 10 min (keeps title fresh)
_USER_TTL = 3600    # re-save a user at most every hour

_seen_chats: dict = {}
_seen_users: dict = {}


def _fresh(store: dict, key, ttl: int, now: float) -> bool:
    """True if `key` was saved recently; otherwise marks it saved now."""
    last = store.get(key)
    if last is not None and now - last < ttl:
        return True
    if len(store) > 100000:
        store.clear()
    store[key] = now
    return False


@Client.on_message(filters.all, group=-5)
async def track_everything(client: Client, message: Message):
    # Never stops propagation, never raises — pure bookkeeping.
    try:
        chat = message.chat
        if not chat:
            return
        now = time.monotonic()
        ctype = enum_name(chat.type)
        user = message.from_user

        if ctype in ("group", "supergroup", "channel"):
            if not _fresh(_seen_chats, chat.id, _CHAT_TTL, now):
                await save_chat(chat.id, chat.title or "", ctype)

        if user and not user.is_bot and not _fresh(_seen_users, user.id, _USER_TTL, now):
            await save_user(user.id, user.username)
    except Exception as e:
        logger.debug(f"tracker: {e!r}")


@Client.on_chat_member_updated(group=-5)
async def track_bot_membership(client: Client, update: ChatMemberUpdated):
    """Bot added to / removed from a group or channel."""
    try:
        member = update.new_chat_member or update.old_chat_member
        if not member or not member.user or not member.user.is_self:
            return
        chat = update.chat
        status = member_status(update.new_chat_member)
        if status in ("left", "banned"):
            await set_chat_active(chat.id, False)
            _seen_chats.pop(chat.id, None)
            logger.info(f"Bot removed from {chat.id} ({chat.title})")
        else:
            await save_chat(chat.id, chat.title or "", enum_name(chat.type))
            _seen_chats[chat.id] = time.monotonic()
            logger.info(f"Bot added/updated in {chat.id} ({chat.title}) as {status}")
    except Exception as e:
        logger.debug(f"tracker(member): {e!r}")
