# ╔══════════════════════════════════════════╗
# ║   Miss Cherry - Rich Message Buttons     ║
# ║   Telegram Bot API 10.3  (Kurigram)      ║
# ╚══════════════════════════════════════════╝
#
# Rich Messages (Bot API 10.1+) carry their buttons INSIDE the message:
#     <tg-button-row><tg-button type="callback_data" style="success" data="x">Text</tg-button></tg-button-row>
# Needs Kurigram >= 2.2.26 (Client.send_rich_message / types.InputRichMessage).
#
# Every menu is described ONCE as `rows` (list of rows of button dicts, see b()).
# send_menu()/edit_menu() render it as a Rich Message and automatically fall
# back to a normal inline keyboard if rich messages are unavailable/rejected.

import html as _html
import re
from urllib.parse import urlparse

from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup

from core.config import cfg
from core.logger import logger
from utils.buttons import btn

try:
    from pyrogram.types import InputRichMessage
except Exception:                      # Pyrogram / Pyrofork / old Kurigram
    InputRichMessage = None

RICH_AVAILABLE = InputRichMessage is not None and hasattr(Client, "send_rich_message")

_BAD_URLS = {"https://t.me", "https://github.com", "https:", "https://", "http://"}


def rich_enabled() -> bool:
    return RICH_AVAILABLE and cfg.RICH_BUTTONS


# ── button spec ────────────────────────────────────────────────────────────
def b(text: str, *, cb: str = None, url: str = None, style: str = None, icon: str = None) -> dict:
    """style: 'primary' (blue) | 'success' (green) | 'danger' (red) | None."""
    return {"text": text, "cb": cb, "url": url, "style": style, "icon": icon}


def _valid(bt: dict) -> bool:
    if bt.get("cb"):
        return 1 <= len(bt["cb"].encode()) <= 64
    url = (bt.get("url") or "").strip()
    if not url or url.rstrip("/") in _BAD_URLS:
        return False
    p = urlparse(url)
    return p.scheme in ("http", "https", "tg") and bool(p.netloc or p.scheme == "tg")


def clean_rows(rows) -> list:
    """Drop buttons with empty/placeholder links (Telegram rejects the WHOLE
    keyboard on one bad URL) and drop empty rows."""
    out = []
    for row in rows or []:
        row = [bt for bt in row if _valid(bt)][:8]       # max 8 per row
        if row:
            out.append(row)
    return out


# ── renderers ──────────────────────────────────────────────────────────────
def _label(bt: dict) -> str:
    """With a custom-emoji icon the leading emoji of the text is redundant."""
    text = bt["text"]
    if bt.get("icon") and cfg.BUTTON_ICONS.get(bt["icon"]):
        text = re.sub(r"^[^\w]+", "", text) or text
    return text


def to_inline(rows):
    """Classic fallback keyboard (InlineKeyboardMarkup) or None."""
    rows = clean_rows(rows)
    if not rows:
        return None
    kb = []
    for row in rows:
        kb.append([
            btn(_label(bt), style=bt.get("style"), icon=bt.get("icon"),
                **({"callback_data": bt["cb"]} if bt.get("cb") else {"url": bt["url"]}))
            for bt in row
        ])
    return InlineKeyboardMarkup(kb)


def _button_html(bt: dict) -> str:
    label = _html.escape(_label(bt), quote=False)
    icon_id = cfg.BUTTON_ICONS.get(bt.get("icon")) if bt.get("icon") else None
    if icon_id and str(icon_id).isdigit():
        label = f'<tg-emoji emoji-id="{icon_id}">⭐</tg-emoji> {label}'
    attrs = ""
    if bt.get("style") in ("primary", "success", "danger"):
        attrs += f' style="{bt["style"]}"'
    if bt.get("cb"):
        attrs = f' type="callback_data"{attrs} data="{_html.escape(bt["cb"], quote=True)}"'
    else:
        attrs = f' type="url"{attrs} url="{_html.escape(bt["url"].strip(), quote=True)}"'
    return f"<tg-button{attrs}>{label}</tg-button>"


def rows_to_rich(rows) -> str:
    return "".join(
        "<tg-button-row>" + "".join(_button_html(bt) for bt in row) + "</tg-button-row>"
        for row in clean_rows(rows)
    )


def text_to_rich(text: str) -> str:
    """Telegram-HTML text (b/i/code/a/blockquote + newlines) -> Rich HTML paragraphs."""
    out = []
    for line in (text or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        out.append(line if line.startswith("<blockquote") else f"<p>{line}</p>")
    return "".join(out)


def build_html(text: str, rows) -> str:
    return text_to_rich(text) + rows_to_rich(rows)


# ── send / edit with automatic fallback ────────────────────────────────────
async def send_menu(message, text: str, rows=None, **kwargs):
    """Reply to `message` with a Rich Message (buttons inside) or a classic one."""
    if rich_enabled():
        try:
            rm = InputRichMessage(html=build_html(text, rows))
            if hasattr(message, "reply_rich"):
                return await message.reply_rich(rich_message=rm)
            return await message._client.send_rich_message(message.chat.id, rich_message=rm)
        except Exception as e:
            logger.warning(f"Rich send failed, using inline keyboard: {e!r}")
    return await message.reply_text(text, reply_markup=to_inline(rows), **kwargs)


async def edit_menu(query, text: str, rows=None):
    """Edit the message under a callback query. Photo messages stay classic."""
    msg = query.message
    try:
        if msg.photo:                                    # START_IMG caption menu
            return await msg.edit_caption(caption=text, reply_markup=to_inline(rows))

        if rich_enabled():
            rm = InputRichMessage(html=build_html(text, rows))
            try:
                try:
                    return await query.edit_message_text(rich_message=rm)
                except TypeError:
                    return await query.edit_message_text("", rich_message=rm)
            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" in str(e).upper():
                    return None
                logger.warning(f"Rich edit failed, using inline keyboard: {e!r}")

        return await msg.edit_text(text, reply_markup=to_inline(rows))
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" in str(e).upper():
            return None
        logger.warning(f"edit_menu failed: {e!r}")
        return None
