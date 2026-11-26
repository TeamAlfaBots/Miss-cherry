# ╔══════════════════════════════════════════╗
# ║   Miss Cherry - Owner Remote Control     ║
# ║   Owner-only, works ONLY in bot's DM     ║
# ╚══════════════════════════════════════════╝
#
#   /list                              → all groups/channels where bot is admin
#   /ban     <user> <chat_id> [time]   → ban in that chat   (time e.g. 1h = temp)
#   /unban   <user> <chat_id>
#   /mute    <user> <chat_id> [time]
#   /unmute  <user> <chat_id>
#   /kick    <user> <chat_id>
#   /promote <user> <chat_id> [full]   → "full" also gives "add new admins"
#   /demote  <user> <chat_id>
#
#   <user> = @username or numeric user id

import asyncio
from html import escape

from pyrogram import Client, filters, errors
from pyrogram.errors import FloodWait
from pyrogram.types import Message, ChatPrivileges

from core.compat import is_admin_status, member_status, enum_name
from core.database import get_all_chats, set_chat_active
from core.filters import owner_filter
from core.logger import logger
from utils.chat_helpers import do_ban, do_unban, do_kick, do_mute, do_unmute, tban_until
from utils.helpers import mention
from utils.log_reporter import send_log
from utils.time_parser import parse_time

DM_OWNER = filters.private & owner_filter

# Errors that mean "the bot is really not in this chat any more".
_GONE = tuple(
    getattr(errors, n) for n in ("ChannelPrivate", "ChannelInvalid", "ChatInvalid")
    if hasattr(errors, n)
)

USAGE = {
    "ban":     "/ban &lt;@user|id&gt; &lt;chat_id&gt; [time]",
    "unban":   "/unban &lt;@user|id&gt; &lt;chat_id&gt;",
    "mute":    "/mute &lt;@user|id&gt; &lt;chat_id&gt; [time]",
    "unmute":  "/unmute &lt;@user|id&gt; &lt;chat_id&gt;",
    "kick":    "/kick &lt;@user|id&gt; &lt;chat_id&gt;",
    "promote": "/promote &lt;@user|id&gt; &lt;chat_id&gt; [full]",
    "demote":  "/demote &lt;@user|id&gt; &lt;chat_id&gt;",
}

CHEATSHEET = (
    "\n<b>Remote commands</b> (DM only):\n"
    "<code>/ban</code> <code>/unban</code> <code>/mute</code> <code>/unmute</code> "
    "<code>/kick</code> <code>/promote</code> <code>/demote</code>\n"
    "Format: <code>/ban @user -1001234567890</code>"
)


def _icon(ctype: str) -> str:
    return "📢" if ctype == "channel" else "👥"


# ══════════════════════════════════════════════
#  /list
# ══════════════════════════════════════════════
@Client.on_message(filters.command("list") & DM_OWNER)
async def cmd_list(client: Client, message: Message):
    status_msg = await message.reply("⏳ <b>Patching... Please wait</b>")
    try:
        await asyncio.wait_for(_do_list(client, message, status_msg), timeout=240)
    except Exception as e:
        # Never leave the owner stuck on "Patching..." — show the real error.
        logger.exception("/list failed")
        try:
            await status_msg.edit(f"❌ <b>/list failed:</b>\n<code>{escape(repr(e))}</code>")
        except Exception:
            pass


async def _do_list(client: Client, message: Message, status_msg: Message):
    me = client.me or await client.get_me()
    chats = await get_all_chats()
    sem = asyncio.Semaphore(8)
    unchecked = 0

    async def check(chat: dict):
        nonlocal unchecked
        cid = chat["_id"]
        async with sem:
            member = None
            for _ in range(2):
                try:
                    member = await asyncio.wait_for(client.get_chat_member(cid, me.id), timeout=20)
                    break
                except FloodWait as e:
                    await asyncio.sleep(min(e.value, 30))
                except _GONE:
                    await set_chat_active(cid, False)
                    return None
                except Exception:
                    # e.g. PeerIdInvalid after a restart with a fresh session:
                    # can't verify now, but the chat is NOT removed from the DB.
                    unchecked += 1
                    return None
            if member is None:
                unchecked += 1
                return None
        if is_admin_status(member.status):
            return chat
        if member_status(member) in ("left", "banned"):
            await set_chat_active(cid, False)
        return None

    results = await asyncio.gather(*(check(c) for c in chats))
    found = [c for c in results if c]

    if not found:
        text = "📋 <b>No chats found where I am admin.</b>"
        if unchecked:
            text += f"\n\n⚠️ {unchecked} chat(s) could not be checked right now."
        return await status_msg.edit(text + CHEATSHEET)

    blocks = []
    for i, c in enumerate(found, 1):
        title = escape(c.get("title") or "Unknown")
        blocks.append(
            f"<b>{i}.</b> {_icon(c.get('type', ''))} <b>{title}</b>\n"
            f"    Chat id - <code>{c['_id']}</code>\n"
        )

    footer = f"\n✅ <b>Total:</b> {len(found)}  (tap an id to copy)"
    if unchecked:
        footer += f"\n⚠️ {unchecked} chat(s) not verified (open after someone messages there)."
    footer += "\n" + CHEATSHEET

    # split into <4000 char messages
    pages, cur = [], ""
    for blk in blocks:
        if len(cur) + len(blk) > 3800:
            pages.append(cur)
            cur = ""
        cur += blk + "\n"
    pages.append(cur)
    pages[-1] += footer

    await status_msg.edit(pages[0])
    for p in pages[1:]:
        await message.reply(p)


# ══════════════════════════════════════════════
#  helpers
# ══════════════════════════════════════════════
async def _resolve_user(client: Client, chat_id: int, token: str):
    target = token.lstrip("@")
    ident = int(target) if target.lstrip("-").isdigit() else f"@{target}"
    try:                                   # chat member list resolves the most
        return (await client.get_chat_member(chat_id, ident)).user
    except Exception:
        pass
    try:
        return await client.get_users(ident)
    except Exception:
        return None


def _parse_args(message: Message):
    """/cmd <user> <chat_id> [rest]  ->  (user_token, chat_id|None, rest)"""
    parts = message.text.split(None, 3)
    if len(parts) < 3:
        return None, None, ""
    cid = parts[2].strip()
    chat_id = int(cid) if cid.lstrip("-").isdigit() else None
    return parts[1], chat_id, (parts[3].strip() if len(parts) > 3 else "")


async def _prepare(client: Client, message: Message, cmd: str):
    """Common validation. Returns (user, chat, rest) or None (error already sent)."""
    token, chat_id, rest = _parse_args(message)
    if token is None or chat_id is None:
        await message.reply(f"❌ Usage: <code>{USAGE[cmd]}</code>")
        return None
    try:
        chat = await client.get_chat(chat_id)
    except Exception as e:
        await message.reply(f"❌ Can't access chat <code>{chat_id}</code>: {escape(str(e))}")
        return None
    user = await _resolve_user(client, chat_id, token)
    if not user:
        await message.reply(
            "❌ User not found. Use the numeric id or @username "
            "(user must be known to the bot / present in that chat)."
        )
        return None
    return user, chat, rest


async def _done(client: Client, message: Message, label: str, user, chat, extra: str = ""):
    title = escape(chat.title or str(chat.id))
    await message.reply(
        f"✅ <b>{label}</b> {mention(user)} in <b>{title}</b>{extra}\n"
        f"Chat id - <code>{chat.id}</code>"
    )
    await send_log(
        client,
        f"🛰 <b>Remote {label}</b>\n"
        f"👤 <b>Owner:</b> {mention(message.from_user)}\n"
        f"🎯 <b>User:</b> {mention(user)} (<code>{user.id}</code>)\n"
        f"💬 <b>Chat:</b> {title} (<code>{chat.id}</code>){extra}",
    )


# ══════════════════════════════════════════════
#  ban / unban / mute / unmute / kick
# ══════════════════════════════════════════════
@Client.on_message(filters.command(["ban", "unban", "mute", "unmute", "kick"]) & DM_OWNER)
async def remote_moderation(client: Client, message: Message):
    cmd = message.command[0].lower()
    prep = await _prepare(client, message, cmd)
    if not prep:
        return
    user, chat, rest = prep

    # optional duration for ban / mute:  /ban @user -100123 2h
    first = rest.split()[0] if rest else ""
    secs = parse_time(first) if first else 0
    until = await tban_until(first) if secs else None

    try:
        if cmd == "ban":
            await do_ban(client, chat.id, user.id, until)
            label = "Temp Banned" if until else "Banned"
        elif cmd == "unban":
            await do_unban(client, chat.id, user.id)
            label = "Unbanned"
        elif cmd == "mute":
            await do_mute(client, chat.id, user.id, until)
            label = "Temp Muted" if until else "Muted"
        elif cmd == "unmute":
            await do_unmute(client, chat.id, user.id)
            label = "Unmuted"
        else:
            await do_kick(client, chat.id, user.id)
            label = "Kicked"
    except Exception as e:
        return await message.reply(f"❌ Failed: {escape(str(e))}")

    await _done(client, message, label, user, chat,
                f"\n⏱ <b>Duration:</b> {first}" if until else "")


# ══════════════════════════════════════════════
#  promote / demote
# ══════════════════════════════════════════════
@Client.on_message(filters.command("promote") & DM_OWNER)
async def remote_promote(client: Client, message: Message):
    prep = await _prepare(client, message, "promote")
    if not prep:
        return
    user, chat, rest = prep
    full = rest.lower().startswith("full")
    is_channel = enum_name(chat.type) == "channel"

    perms = dict(
        can_manage_chat=True,
        can_change_info=True,
        can_delete_messages=True,
        can_manage_video_chats=True,
        can_invite_users=True,
        can_promote_members=full,
    )
    if is_channel:
        perms.update(can_post_messages=True, can_edit_messages=True)
    else:
        perms.update(can_restrict_members=True, can_pin_messages=True)

    try:
        await client.promote_chat_member(chat.id, user.id, privileges=ChatPrivileges(**perms))
    except Exception as e:
        return await message.reply(f"❌ Failed: {escape(str(e))}")
    await _done(client, message, "Promoted", user, chat,
                "\n👑 <b>Rights:</b> full (can add admins)" if full else "")


@Client.on_message(filters.command("demote") & DM_OWNER)
async def remote_demote(client: Client, message: Message):
    prep = await _prepare(client, message, "demote")
    if not prep:
        return
    user, chat, _rest = prep
    try:
        await client.promote_chat_member(
            chat.id, user.id,
            privileges=ChatPrivileges(
                can_manage_chat=False, can_change_info=False, can_delete_messages=False,
                can_manage_video_chats=False, can_restrict_members=False,
                can_promote_members=False, can_invite_users=False, can_pin_messages=False,
                can_post_messages=False, can_edit_messages=False,
            ),
        )
    except Exception as e:
        return await message.reply(f"❌ Failed: {escape(str(e))}")
    await _done(client, message, "Demoted", user, chat)
