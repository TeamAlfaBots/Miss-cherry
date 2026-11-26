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
    "support": "4956475826762679249",
    "updates": "4956290155326473271",
    "help": "4958534696645428119",          # ❓ Help & Commands
    "language": "4956560549287560231",      # 🌐 Language
    "info": "4956324463525233747",          # 🪧 Info
    # ── info menu ──
    "owner": "5190736541521025564",
    "developer": "5190498849440931467",
    "source": "5431721976769027887",
    # ── help menu modules ──
    "m_admin": "6082543233034883875",
    "m_antiflood": "6084620889104585357",
    "m_antiraid": "6082147683726790806",
    "m_approval": "4956721670690702265",
    "m_bans": "6082248125831975582",
    "m_blocklist": "6082176507252314811",
    "m_filters": "6082550981155888491",
    "m_greetings": "6082460438950320151",
    "m_language": "4956560549287560231",
    "m_pin": "6084637175620571440",
    "m_purge": "5395695537687123235",
    "m_report": "5395695537687123235",
    "m_rules": "5395444784611480792",
    "m_warning": "5447644880824181073",
    "m_sudo": "6172232131679360513",
    "m_chatbot": "5330550994159815930",
    "docs": "5253911945622332753",
    # ── language menu ──
    "l_en": "5382062173323276195", "l_hi": "6267008582294705964", "l_bh": "6267008582294705964", "l_ta": "6267008582294705964", "l_ar": "", "l_ru": "",
    # ── common ──
    "back": "5255831443816327915",
    "close": "5255831443816327915",
    "confirm": "6267008582294705964",       # ✅ Confirm & Promote
}

# merge into config (env BUTTON_ICONS wins)
from core.config import cfg  # noqa: E402

cfg.BUTTON_ICONS = {**{k: v for k, v in ICONS.items() if v}, **cfg.BUTTON_ICONS}
