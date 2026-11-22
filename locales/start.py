# ╔══════════════════════════════════════════╗
# ║      Miss Cherry - Start Module          ║
# ╚══════════════════════════════════════════╝

import re
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from core.config import cfg
from core.translator import _
from core.database import set_language, get_language, save_chat, save_user
from utils.helpers import mention
from utils.keyboard import (
    start_kb, start_rows, help_rows, info_rows, lang_rows, back_close_rows
)
from utils.rich import send_menu, edit_menu
from core.logger import logger
from utils.log_reporter import log_bot_started


# ══════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════

HELP_TITLE = "📚 <b>Miss Cherry Help Menu</b>\n\nChoose a module:"


@Client.on_message(filters.command("start") & filters.private)
async def start_private(client: Client, message: Message):
    user = message.from_user
    await save_user(user.id, user.username)
    text = await _(0, "start.welcome", name=mention(user))
    if cfg.START_IMG:      # photo + caption can't be a Rich Message -> classic keyboard
        await message.reply_photo(photo=cfg.START_IMG, caption=text, reply_markup=start_kb())
    else:
        await send_menu(message, text, start_rows())


@Client.on_message(filters.command("start") & ~filters.private)
async def start_group(client: Client, message: Message):
    try:
        user = message.from_user
        await save_chat(message.chat.id, message.chat.title)
        if user:
            await save_user(user.id, user.username)
        await log_bot_started(client, message)
        text = await _(message.chat.id, "start.group_welcome",
                       name=mention(user) if user else "")
        await send_menu(message, text, start_rows())
    except Exception as e:
        logger.error(f"start_group failed: {e!r}")


# ══════════════════════════════════════════════
#  /help
# ══════════════════════════════════════════════

@Client.on_message(filters.command("help"))
async def help_cmd(client: Client, message: Message):
    await send_menu(message, HELP_TITLE, help_rows())


# ══════════════════════════════════════════════
#  CALLBACKS
# ══════════════════════════════════════════════

@Client.on_callback_query(filters.regex("^start_menu$"))
async def cb_start(client: Client, query: CallbackQuery):
    text = await _(0, "start.welcome", name=mention(query.from_user))
    await edit_menu(query, text, start_rows())


@Client.on_callback_query(filters.regex("^help_menu$"))
async def cb_help(client: Client, query: CallbackQuery):
    await edit_menu(query, HELP_TITLE, help_rows())


@Client.on_callback_query(filters.regex("^info_menu$"))
async def cb_info(client: Client, query: CallbackQuery):
    text = await _(query.message.chat.id, "info.title")
    await edit_menu(query, text, info_rows())


@Client.on_callback_query(filters.regex("^lang_menu$"))
async def cb_lang_menu(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    lang = (await get_language(chat_id)).upper()
    text = await _(chat_id, "language.current", lang=lang)
    await edit_menu(query, text, lang_rows())


@Client.on_callback_query(filters.regex(r"^setlang_(\w+)$"))
async def cb_setlang(client: Client, query: CallbackQuery):
    lang = query.data.split("_", 1)[1]
    chat_id = query.message.chat.id
    await set_language(chat_id, lang)
    text = await _(chat_id, "language.set", lang=lang.upper())
    await query.answer(re.sub(r"<[^>]+>", "", text), show_alert=False)
    new_text = await _(chat_id, "language.current", lang=lang.upper())
    await edit_menu(query, new_text, lang_rows())


@Client.on_callback_query(filters.regex("^close$"))
async def cb_close(client: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        await query.answer()


# ── Help module callbacks ──────────────────────
HELP_TEXTS = {
    "admin": """👮 <b>Admin</b>

Make it easy to promote and demote users!

<b>Commands:</b>
- <code>/promote</code> — Promote a user
- <code>/demote</code> — Demote a user
- <code>/adminlist</code> — List all admins
- <code>/admincache</code> — Refresh admin cache
- <code>/anonadmin</code> &lt;yes/no&gt; — Allow anon admins
- <code>/adminerror</code> &lt;yes/no&gt; — Show error to normal users""",

    "antiflood": """🌊 <b>Antiflood</b>

Stop users from flooding the chat!

<b>Commands:</b>
- <code>/flood</code> — View current settings
- <code>/setflood</code> &lt;number/off&gt; — Set message limit
- <code>/setfloodtimer</code> &lt;count&gt; &lt;time&gt; — Set timed flood
- <code>/floodmode</code> &lt;ban/mute/kick/tban/tmute&gt; — Set action
- <code>/clearflood</code> &lt;yes/no&gt; — Delete flood messages""",

    "antiraid": """🛡 <b>AntiRaid</b>

Stop raid attacks on your group!

<b>Commands:</b>
- <code>/antiraid</code> &lt;time/off&gt; — Toggle antiraid
- <code>/raidtime</code> &lt;time&gt; — Set raid duration
- <code>/raidactiontime</code> &lt;time&gt; — Set ban duration
- <code>/autoantiraid</code> &lt;number/off&gt; — Auto trigger""",

    "approval": """✅ <b>Approval</b>

Trust certain users to bypass restrictions!

<b>Commands:</b>
- <code>/approval</code> — Check approval status
- <code>/approve</code> — Approve a user
- <code>/unapprove</code> — Unapprove a user
- <code>/approved</code> — List approved users
- <code>/unapproveall</code> — Remove all approvals""",

    "bans": """🔨 <b>Bans</b>

Ban, mute, and kick users!

<b>Commands:</b>
- <code>/ban</code> <code>/dban</code> <code>/sban</code> — Ban user
- <code>/tban</code> &lt;time&gt; — Temp ban
- <code>/unban</code> — Unban user
- <code>/mute</code> <code>/dmute</code> <code>/smute</code> — Mute user
- <code>/tmute</code> &lt;time&gt; — Temp mute
- <code>/unmute</code> — Unmute user
- <code>/kick</code> <code>/dkick</code> <code>/skick</code> — Kick user
- <code>/kickme</code> — Kick yourself""",

    "blocklist": """🚫 <b>Blocklist</b>

Block specific words and patterns!

<b>Commands:</b>
- <code>/addblocklist</code> &lt;trigger&gt; — Add trigger
- <code>/rmblocklist</code> &lt;trigger&gt; — Remove trigger
- <code>/unblocklistall</code> — Clear all (creator only)
- <code>/blocklist</code> — List all triggers
- <code>/blocklistmode</code> &lt;mode&gt; — Set action
- <code>/blocklistdelete</code> &lt;yes/no&gt; — Delete messages
- <code>/setblocklistreason</code> &lt;reason&gt; — Set reason

<b>Patterns:</b> <code>?</code> <code>*</code> <code>**</code>""",

    "filters": """🔍 <b>Filters</b>

Auto-reply to trigger words!

<b>Commands:</b>
- <code>/filter</code> &lt;trigger&gt; &lt;reply&gt; — Add filter
- <code>/filters</code> — List all filters
- <code>/stop</code> &lt;trigger&gt; — Remove filter
- <code>/stopall</code> — Remove all filters""",

    "greetings": """👋 <b>Greetings</b>

Welcome new members!

<b>Commands:</b>
- <code>/welcome</code> &lt;yes/no&gt; — Toggle welcome
- <code>/goodbye</code> &lt;yes/no&gt; — Toggle goodbye
- <code>/setwelcome</code> &lt;text&gt; — Set welcome message
- <code>/resetwelcome</code> — Reset welcome
- <code>/setgoodbye</code> &lt;text&gt; — Set goodbye message
- <code>/resetgoodbye</code> — Reset goodbye
- <code>/cleanwelcome</code> &lt;yes/no&gt; — Auto-delete old welcomes

<b>Fillings:</b> <code>{mention}</code> <code>{first}</code> <code>{username}</code> <code>{chatname}</code> <code>{id}</code>""",

    "language": """🌐 <b>Language</b>

Change bot reply language!

<b>Available:</b>
🇬🇧 EN | 🇮🇳 HI | 🇮🇳 BH | 🇮🇳 TA | 🇸🇦 AR | 🇷🇺 RU

<b>Commands:</b>
- <code>/setlang</code> &lt;lang&gt; — Set language""",

    "pin": """📌 <b>Pin</b>

Pin and manage messages!

<b>Commands:</b>
- <code>/pinned</code> — Get pinned message
- <code>/pin</code> — Pin replied message
- <code>/permapin</code> &lt;text&gt; — Pin custom message
- <code>/unpin</code> — Unpin message
- <code>/unpinall</code> — Unpin all
- <code>/antichannelpin</code> &lt;yes/no&gt; — Stop auto-pin
- <code>/cleanlinked</code> &lt;yes/no&gt; — Delete linked channel messages""",

    "purge": """🗑 <b>Purge</b>

Delete many messages at once!

<b>Commands:</b>
- <code>/purge</code> — Delete from reply to now
- <code>/purge &lt;X&gt;</code> — Delete X messages
- <code>/spurge</code> — Silent purge
- <code>/del</code> — Delete replied message
- <code>/purgefrom</code> — Mark start point
- <code>/purgeto</code> — Delete from start to here""",

    "report": """🚨 <b>Report</b>

Let users report rule-breakers!

<b>User Commands:</b>
- <code>/report</code> — Report a message (reply)
- <code>@admin</code> — Same as /report

<b>Admin Commands:</b>
- <code>/reports</code> &lt;yes/no&gt; — Enable/disable reports""",

    "rules": """📜 <b>Rules</b>

Set and manage group rules!

<b>User Commands:</b>
- <code>/rules</code> — View rules

<b>Admin Commands:</b>
- <code>/setrules</code> &lt;text&gt; — Set rules
- <code>/resetrules</code> — Reset rules
- <code>/privaterules</code> &lt;yes/no&gt; — Send rules in PM""",

    "warning": """⚠️ <b>Warnings</b>

Keep members in check!

<b>Commands:</b>
- <code>/warn</code> &lt;reason&gt; — Warn a user
- <code>/dwarn</code> — Warn + delete message
- <code>/swarn</code> — Silent warn
- <code>/warns</code> — View user's warnings
- <code>/rmwarn</code> — Remove last warning
- <code>/resetwarn</code> — Reset user warnings
- <code>/resetallwarns</code> — Reset all warnings
- <code>/warnmode</code> &lt;mode&gt; — Set warn action
- <code>/warnlimit</code> &lt;number&gt; — Set warn limit
- <code>/warntime</code> &lt;time&gt; — Set warn expiry""",

    "sudo": """🔑 <b>Sudo</b>

Grant trusted users owner-level access!

<b>Owner Commands:</b>
- <code>/addsudo</code> — Add sudo user
- <code>/rmsudo</code> — Remove sudo user
- <code>/sudolist</code> — List all sudo users""",

    "chatbot": """🤖 <b>Chatbot</b> (DeepSeek AI)

Miss Cherry chats with your members!

<b>Commands:</b>
- <code>/chatbot on</code> — Enable
- <code>/chatbot off</code> — Disable (default)

<b>Smart Logic:</b>
• Direct message → Miss Cherry replies 🍒
• Reply to another user → Miss Cherry stays silent 🤫
• Chat history saved in DB — survives restarts! 🧠"""
}


@Client.on_callback_query(filters.regex(r"^help_(?!menu$)(\w+)$"))
async def cb_help_module(client: Client, query: CallbackQuery):
    module = query.data.replace("help_", "", 1)
    text = HELP_TEXTS.get(module, "❌ Module not found.")
    await edit_menu(query, text, back_close_rows("help_menu"))
