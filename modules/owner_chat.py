# ╔══════════════════════════════════════════╗
# ║   Miss Cherry - Owner Chat (fun + boss)  ║
# ║   Works only for the bot OWNER, in groups║
# ╚══════════════════════════════════════════╝
#
#   Owner:  "Hello cherry"                      → Bot: "Yes boss"
#   Owner:  "Mujhe admin bnao yrr ..."          → Bot: "Ofc sir"
#                                                  "Apko admin banane ka process chalu"
#                                                  (promotes the owner)
#                                                  "Congratulations aap admin ho boss"
#
# The "make me admin" request is only understood when it is clearly meant
# for the bot:  the owner said "cherry" in it, replied to the bot's message,
# or greeted the bot ("Hello cherry") in that chat in the last 15 minutes.
# So normal owner <-> member talk in a group is never hijacked.

import asyncio
import re
import time
from html import escape

from pyrogram import Client, filters
from pyrogram.types import Message, ChatPrivileges

from core.compat import is_admin_status
from core.filters import owner_filter
from core.logger import logger

CONTEXT_SECS = 900          # "Hello cherry" keeps the chat "open" for 15 min
_greeted: dict = {}         # chat_id -> monotonic time of last greeting

_GREETING = re.compile(r"^\W*(hello|helo|hlo|hi+|hey+|namaste)\W+(miss\s+)?cherry\b", re.I)
_VERB = re.compile(r"(?:\bban|\bbn)a\w*|\bpromote\b|\bmake\b|बना", re.I)

# rights the bot may hand over (only those the bot itself has)
_RIGHTS = (
    "can_manage_chat", "can_change_info", "can_delete_messages",
    "can_restrict_members", "can_invite_users", "can_pin_messages",
    "can_manage_video_chats", "can_promote_members",
)

T_YES = "Yes boss! 🫡🍒"
T_OFC = "Ofc sir 😌"
T_PROCESS = "Apko admin banane ka process chalu ⚙️..."
T_DONE = "🎉 Congratulations aap admin ho boss! 👑"
T_ALREADY = "Boss, aap to pehle se hi admin ho 😄"
T_BOT_NOT_ADMIN = "Sorry boss 🥺 main is group mein admin nahi hoon, pehle mujhe admin banao."
T_NO_RIGHT = ("Sorry boss 🥺 mere paas <b>Add new admins</b> ka right nahi hai. "
              "Wo permission do, phir bolna!")


def _is_admin_request(t: str) -> bool:
    has_admin = "admin" in t or "एडमिन" in t
    return bool(has_admin and _VERB.search(t))


def _meant_for_bot(message: Message, t: str) -> bool:
    if "cherry" in t:
        return True
    rep = message.reply_to_message
    if rep and rep.from_user and rep.from_user.is_self:
        return True
    last = _greeted.get(message.chat.id)
    return last is not None and time.monotonic() - last < CONTEXT_SECS


@Client.on_message(filters.text & ~filters.private & owner_filter, group=-3)
async def owner_chat(client: Client, message: Message):
    t = (message.text or "").strip().lower()
    if not t or t.startswith("/"):
        return
    logger.info(f"owner_chat: owner message seen in {message.chat.id}: {t[:40]!r}")
    # "@Cherry_mngbot hello cherry" also works (mentions reach the bot even
    # when Telegram privacy mode hides normal group messages).
    t = re.sub(r"^@\w+[\s,:\-]*", "", t)

    # ── 1. "Hello cherry" ────────────────────────────────
    if _GREETING.match(t):
        _greeted[message.chat.id] = time.monotonic()
        await message.reply(T_YES)
        message.stop_propagation()
        return

    # ── 2. "make me admin" ───────────────────────────────
    if not (_is_admin_request(t) and _meant_for_bot(message, t)):
        return                                  # normal chat — leave untouched

    chat_id, owner_id = message.chat.id, message.from_user.id
    await message.reply(T_OFC)
    await asyncio.sleep(1)

    try:
        me = client.me or await client.get_me()
        owner_member = await client.get_chat_member(chat_id, owner_id)
        if is_admin_status(owner_member.status):
            await message.reply(T_ALREADY)
        else:
            bot_member = await client.get_chat_member(chat_id, me.id)
            bp = getattr(bot_member, "privileges", None)
            if not is_admin_status(bot_member.status) or bp is None:
                await message.reply(T_BOT_NOT_ADMIN)
            elif not getattr(bp, "can_promote_members", False):
                await message.reply(T_NO_RIGHT)
            else:
                await message.reply(T_PROCESS)
                await asyncio.sleep(1)
                perms = {r: True for r in _RIGHTS if getattr(bp, r, False)}
                await client.promote_chat_member(
                    chat_id, owner_id, privileges=ChatPrivileges(**perms)
                )
                await message.reply(T_DONE)
    except Exception as e:
        logger.warning(f"owner_chat promote failed in {chat_id}: {e!r}")
        await message.reply(f"❌ Admin nahi bana paayi boss: <code>{escape(str(e))}</code>")

    message.stop_propagation()
