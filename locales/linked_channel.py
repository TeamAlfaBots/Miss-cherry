# ╔══════════════════════════════════════════╗
# ║   Miss Cherry - Linked Channel Module    ║
# ║   /antichannelpin  /cleanlinked          ║
# ╚══════════════════════════════════════════╝

from pyrogram import Client, filters
from pyrogram.types import Message

from core.database import get_greeting


def _from_channel(msg) -> bool:
    """True for a post that Telegram auto-forwarded from the linked channel."""
    if getattr(msg, "is_automatic_forward", False):
        return True
    return bool(getattr(msg, "sender_chat", None) and getattr(msg, "forward_from_chat", None))


@Client.on_message(filters.pinned_message & ~filters.private, group=2)
async def anti_channel_pin(client: Client, message: Message):
    data = await get_greeting(message.chat.id)
    if not data.get("antichannelpin"):
        return
    pinned = message.pinned_message
    if pinned and _from_channel(pinned):
        try:
            await client.unpin_chat_message(message.chat.id, pinned.id)
            await message.delete()
        except Exception:
            pass


@Client.on_message(~filters.private & ~filters.service, group=3)
async def clean_linked(client: Client, message: Message):
    if not _from_channel(message):
        return
    data = await get_greeting(message.chat.id)
    if data.get("cleanlinked"):
        try:
            await message.delete()
        except Exception:
            pass
