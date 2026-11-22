# ╔══════════════════════════════════════════╗
# ║       Miss Cherry - Menus / Keyboards    ║
# ║   Rich Message buttons (Bot API 10.3)    ║
# ╚══════════════════════════════════════════╝
# *_rows()  -> button specs, rendered by utils.rich (Rich Message buttons)
# *_kb()    -> same menu as a classic InlineKeyboardMarkup (photo captions / fallback)

from core.config import cfg
from utils.rich import b, to_inline


def start_rows():
    return [
        [b("📨 Support", url=cfg.SUPPORT_LINK, style="primary"),
         b("📢 Updates", url=cfg.UPDATE_LINK, style="primary")],
        [b("❓ Help & Commands", cb="help_menu", style="success", icon="help")],
        [b("🌐 Language", cb="lang_menu", style="danger"),
         b("🪧 Info", cb="info_menu", style="danger")],
    ]


def info_rows():
    owner = cfg.OWNER_USERNAME.lstrip("@")
    dev = cfg.DEVELOPER_USERNAME.lstrip("@")
    return [
        [b("👑 Owner", url=f"https://t.me/{owner}" if owner else "", style="primary"),
         b("👨‍💻 Developer", url=f"https://t.me/{dev}" if dev else "", style="primary")],
        [b("📂 Source", url=cfg.SOURCE_LINK, style="primary")],
        [b("◀️ Back", cb="start_menu", icon="back"),
         b("✖️ Close", cb="close", style="danger", icon="close")],
    ]


def help_rows():
    return [
        [b("👮 Admin", cb="help_admin", style="danger"),
         b("🌊 Antiflood", cb="help_antiflood", style="danger"),
         b("🛡 AntiRaid", cb="help_antiraid", style="danger")],
        [b("✅ Approval", cb="help_approval", style="primary"),
         b("🔨 Bans", cb="help_bans", style="primary"),
         b("🚫 Blocklist", cb="help_blocklist", style="primary")],
        [b("🔍 Filters", cb="help_filters", style="success"),
         b("👋 Greetings", cb="help_greetings", style="success"),
         b("🌐 Language", cb="help_language", style="success")],
        [b("📌 Pin", cb="help_pin", style="danger"),
         b("🗑 Purge", cb="help_purge", style="danger"),
         b("🚨 Report", cb="help_report", style="danger")],
        [b("📜 Rules", cb="help_rules", style="primary"),
         b("⚠️ Warning", cb="help_warning", style="primary"),
         b("🔑 Sudo", cb="help_sudo", style="primary")],
        [b("🤖 Chatbot", cb="help_chatbot", style="success")],
        [b("📖 Miss Cherry Docs", url=cfg.DOCS_URL, style="success")],
        [b("◀️ Back", cb="start_menu", style="primary", icon="back"),
         b("✖️ Close", cb="close", style="danger", icon="close")],
    ]


def lang_rows():
    langs = [("🇬🇧 English", "en"), ("🇮🇳 हिन्दी", "hi"), ("🇮🇳 Bhojpuri", "bh"),
             ("🇮🇳 தமிழ்", "ta"), ("🇸🇦 العربية", "ar"), ("🇷🇺 Русский", "ru")]
    rows = [[b(n, cb=f"setlang_{c}", style="success") for n, c in langs[i:i + 2]]
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
