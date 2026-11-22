# ╔══════════════════════════════════════════╗
# ║   Miss Cherry - Button helpers           ║
# ║   Bot API 9.4+ style / custom emoji      ║
# ╚══════════════════════════════════════════╝

from pyrogram.types import InlineKeyboardButton

try:                                   # Kurigram / Pyrofork
    from pyrogram.enums import ButtonStyle
except Exception:                      # very old pyrogram: no coloured buttons
    ButtonStyle = None

from core.config import cfg
from core.logger import logger

STYLES = ("primary", "success", "danger")


def _style(style):
    """'primary' | 'success' | 'danger' | ButtonStyle -> ButtonStyle (or None)."""
    if style is None or ButtonStyle is None:
        return None
    if isinstance(style, str):
        return getattr(ButtonStyle, style.upper(), None)
    return style


def btn(text: str, *, style=None, icon: str = None, **kwargs) -> InlineKeyboardButton:
    """Classic inline-keyboard button with colour + optional custom-emoji icon."""
    st = _style(style)
    if st is not None:
        kwargs["style"] = st

    icon_id = cfg.BUTTON_ICONS.get(icon) if icon else None
    if icon_id:
        try:
            kwargs["icon_custom_emoji_id"] = int(icon_id)
        except (TypeError, ValueError):
            logger.warning(f"Bad custom emoji id for icon '{icon}': {icon_id!r}")

    try:
        return InlineKeyboardButton(text, **kwargs)
    except TypeError:
        kwargs.pop("style", None)
        kwargs.pop("icon_custom_emoji_id", None)
        return InlineKeyboardButton(text, **kwargs)
