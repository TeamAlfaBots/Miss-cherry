# ╔══════════════════════════════════════════╗
# ║  Miss Cherry - Premium (custom) emoji    ║
# ║  icons for inline / rich buttons         ║
# ╚══════════════════════════════════════════╝
# Put the custom_emoji_id (a long number, as a string) next to a button name.
# Empty "" = no icon for that button (normal emoji stays).
# The BUTTON_ICONS env var (JSON) still works and overrides this file.
#
# How to get an id: send the premium emoji to @RawDataBot / @ShowJsonBot and
# copy "custom_emoji_id" from the entities part.
# Needs: bot owner with Telegram Premium (or a bot with Fragment usernames).

ICONS = {
    # ── /start menu ──
    "support": "",
    "updates": "",
    "help": "",          # ❓ Help & Commands
    "language": "",      # 🌐 Language
    "info": "",          # 🪧 Info
    # ── info menu ──
    "owner": "",
    "developer": "",
    "source": "",
    # ── help menu modules ──
    "m_admin": "",
    "m_antiflood": "",
    "m_antiraid": "",
    "m_approval": "",
    "m_bans": "",
    "m_blocklist": "",
    "m_filters": "",
    "m_greetings": "",
    "m_language": "",
    "m_pin": "",
    "m_purge": "",
    "m_report": "",
    "m_rules": "",
    "m_warning": "",
    "m_sudo": "",
    "m_chatbot": "",
    "docs": "",
    # ── language menu ──
    "l_en": "", "l_hi": "", "l_bh": "", "l_ta": "", "l_ar": "", "l_ru": "",
    # ── common ──
    "back": "",
    "close": "",
    "confirm": "",       # ✅ Confirm & Promote
}

# merge into config (env BUTTON_ICONS wins)
from core.config import cfg  # noqa: E402

cfg.BUTTON_ICONS = {**{k: v for k, v in ICONS.items() if v}, **cfg.BUTTON_ICONS}
