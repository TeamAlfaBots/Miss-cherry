# ╔══════════════════════════════════════════╗
# ║       Miss Cherry - Menus / Keyboards    ║
# ║   Rich Message buttons (Bot API 10.3)    ║
# ╚══════════════════════════════════════════╝
# *_rows()  -> button specs, rendered by utils.rich (Rich Message buttons)
# *_kb()    -> same menu as a classic InlineKeyboardMarkup (photo captions / fallback)

from core.config import cfg
from utils import icons  # noqa: F401  (merges ICONS into cfg.BUTTON_ICONS)
from utils.rich import b, to_inline


def start_rows():
    return [
        [b("📨 Support", url=cfg.SUPPORT_LINK, style="primary", icon="support"),
         b("📢 Updates", url=cfg.UPDATE_LINK, style="primary", icon="updates")],
        [b("❓ Help & Commands", cb="help_menu", style="success", icon="help")],
        [b("🌐 Language", cb="lang_menu", style="danger", icon="language"),
         b("🪧 Info", cb="info_menu", style="danger", icon="info")],
    ]


def info_rows():
    owner = cfg.OWNER_USERNAME.lstrip("@")
    dev = cfg.DEVELOPER_USERNAME.lstrip("@")
    return [
        [b("👑 Owner", url=f"https://t.me/{owner}" if owner else "", style="primary", icon="owner"),
         b("👨‍💻 Developer", url=f"https://t.me/{dev}" if dev else "", style="primary", icon="developer")],
        [b("📂 Source", url=cfg.SOURCE_LINK, style="primary", icon="source")],
        [b("◀️ Back", cb="start_menu", icon="back"),
         b("✖️ Close", cb="close", style="danger", icon="close")],
    ]


def help_rows():
    return [
        [b("👮 Admin", cb="help_admin", style="danger", icon="m_admin"),
         b("🌊 Antiflood", cb="help_antiflood", style="danger", icon="m_antiflood"),
         b("🛡 AntiRaid", cb="help_antiraid", style="danger", icon="m_antiraid")],
        [b("✅ Approval", cb="help_approval", style="primary", icon="m_approval"),
         b("🔨 Bans", cb="help_bans", style="primary", icon="m_bans"),
         b("🚫 Blocklist", cb="help_blocklist", style="primary", icon="m_blocklist")],
        [b("🔍 Filters", cb="help_filters", style="success", icon="m_filters"),
         b("👋 Greetings", cb="help_greetings", style="success", icon="m_greetings"),
         b("🌐 Language", cb="help_language", style="success", icon="m_language")],
        [b("📌 Pin", cb="help_pin", style="danger", icon="m_pin"),
         b("🗑 Purge", cb="help_purge", style="danger", icon="m_purge"),
         b("🚨 Report", cb="help_report", style="danger", icon="m_report")],
        [b("📜 Rules", cb="help_rules", style="primary", icon="m_rules"),
         b("⚠️ Warning", cb="help_warning", style="primary", icon="m_warning"),
         b("🔑 Sudo", cb="help_sudo", style="primary", icon="m_sudo")],
        [b("🤖 Chatbot", cb="help_chatbot", style="success", icon="m_chatbot")],
        [b("📖 Miss Cherry Docs", url=cfg.DOCS_URL, style="success", icon="docs")],
        [b("◀️ Back", cb="start_menu", style="primary", icon="back"),
         b("✖️ Close", cb="close", style="danger", icon="close")],
    ]


def lang_rows():
    langs = [("🇬🇧 English", "en"), ("🇮🇳 हिन्दी", "hi"), ("🇮🇳 Bhojpuri", "bh"),
             ("🇮🇳 தமிழ்", "ta"), ("🇸🇦 العربية", "ar"), ("🇷🇺 Русский", "ru")]
    rows = [[b(n, cb=f"setlang_{c}", style="success", icon=f"l_{c}") for n, c in langs[i:i + 2]]
            for i in range(0, len(langs), 2)]
    rows.append([b("◀️ Back", cb="start_menu", style="primary", icon="back"),
                 b("✖️ Close", cb="close", style="danger", icon="close")])
    return rows


def back_close_rows(back_data: str = "help_menu"):
    return [[b("◀️ Back", cb=back_data, style="primary", icon="back"),
             b("✖️ Close", cb="close", style="danger", icon="close")]]


def back_rows(back_data: str = "help_menu"):
    return [[b("◀️ Back", cb=back_data, style="primary", icon="back")]]


# classic keyboards (photo captions / fallback)
def start_kb():            return to_inline(start_rows())
def info_kb():             return to_inline(info_rows())
def help_kb():             return to_inline(help_rows())
def lang_kb():             return to_inline(lang_rows())
def back_close_kb(back_data: str = "help_menu"): return to_inline(back_close_rows(back_data))
def back_kb(back_data: str = "help_menu"):       return to_inline(back_rows(back_data))
