# ╔══════════════════════════════════════════╗
# ║      Miss Cherry - Sudo Module           ║
# ╚══════════════════════════════════════════╝

from pyrogram import Client, filters
from pyrogram.types import Message

from core.config import cfg
from core.filters import owner_filter, sudo_filter
from core.translator import _
from core.database import add_sudo, remove_sudo, get_sudos
from utils.helpers import get_target_user, mention


@Client.on_message(filters.command("addsudo") & owner_filter)
async def cmd_addsudo(client: Client, message: Message):
    try:
        user, _reason = await get_target_user(client, message)
    except ValueError:
        user = None
    if not user:
        return await message.reply(await _(message.chat.id, "general.no_user"))
    if user.id in cfg.OWNER_ID:
        return await message.reply(await _(message.chat.id, "sudo.already_owner"))
    await add_sudo(user.id)
    await message.reply(await _(message.chat.id, "sudo.added", name=mention(user)))


@Client.on_message(filters.command("rmsudo") & owner_filter)
async def cmd_rmsudo(client: Client, message: Message):
    try:
        user, _reason = await get_target_user(client, message)
    except ValueError:
        user = None
    if not user:
        return await message.reply(await _(message.chat.id, "general.no_user"))
    await remove_sudo(user.id)
    await message.reply(await _(message.chat.id, "sudo.removed", name=mention(user)))


@Client.on_message(filters.command("sudolist") & sudo_filter)
async def cmd_sudolist(client: Client, message: Message):
    ids = await get_sudos()
    if not ids:
        return await message.reply(await _(message.chat.id, "sudo.list_empty"))
    lines = []
    for uid in ids:
        try:
            lines.append(f"• {mention(await client.get_users(uid))} (<code>{uid}</code>)")
        except Exception:
            lines.append(f"• <code>{uid}</code>")
    await message.reply(await _(message.chat.id, "sudo.list_title", list="\n".join(lines)))
