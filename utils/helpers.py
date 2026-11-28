# ╔══════════════════════════════════════════╗
# ║       Miss Cherry - Helpers              ║
# ╚══════════════════════════════════════════╝

from html import escape
from pyrogram.types import Message


def mention(user) -> str:
    name = escape(user.first_name or "User")
    return f'<a href="tg://user?id={user.id}">{name}</a>'


async def get_target_user(client, message: Message):
    """
    Returns (user, reason) from reply / mention / user_id.
    If the replied-to account has been deleted (Telegram discards its
    identity, so it can never be resolved) it replies with a clear
    message and stops the command quietly.
    """
    reason = ""

    if message.reply_to_message:
        if message.reply_to_message.from_user:
            user = message.reply_to_message.from_user
            parts = message.text.split(None, 1)
            reason = parts[1] if len(parts) > 1 else ""
            return user, reason
        elif message.reply_to_message.sender_chat is None:
            # No from_user AND no sender_chat on a real message almost
            # always means the account has been deleted.
            # Used to raise ValueError -> uncaught crash in /approve, /warn,
            # /promote ... Now every command answers politely and stops here.
            await message.reply(
                "❌ Ye message kisi <b>deleted account</b> ka hai, Telegram ab uski "
                "pehchaan nahi deta. Command ko user ki <b>ID</b> ya <b>@username</b> ke saath chalao."
            )
            message.stop_propagation()      # silent stop, no error in logs

    args = message.text.split(None, 2)
    if len(args) < 2:
        return None, ""

    target = args[1]
    reason = args[2] if len(args) > 2 else ""
    target_clean = target.lstrip("@")
    is_numeric = target_clean.lstrip("-").isdigit()
    # get_chat_member needs an int id or a "@username" string — never a
    # bare username with the "@" stripped off, or Pyrogram can't resolve it.
    member_lookup = int(target_clean) if is_numeric else f"@{target_clean}"

    # Try resolving via the chat member list first when we have a chat
    # context — this can resolve users (and their access_hash) that a
    # bare get_users() call cannot, since the bot may never have
    # interacted with that user directly.
    try:
        member = await client.get_chat_member(message.chat.id, member_lookup)
        return member.user, reason
    except Exception:
        pass

    try:
        user = await client.get_users(member_lookup)
        return user, reason
    except Exception:
        return None, reason
        
