# ╔══════════════════════════════════════════╗
# ║       Miss Cherry - Config               ║
# ╚══════════════════════════════════════════╝

import os
import json
from dotenv import load_dotenv

load_dotenv(".env")


class Config:
    # ── Bot Credentials ──────────────────────
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    API_ID: int    = int(os.getenv("API_ID", 0))
    API_HASH: str  = os.getenv("API_HASH", "")

    # ── Owners ───────────────────────────────
    OWNER_ID: list = [
        int(x) for x in os.getenv("OWNER_ID", "").replace(",", " ").split() if x.lstrip("-").isdigit()
    ]

    # ── Log Group ─────────────────────────────
    LOG_GROUP_ID: int = int(os.getenv("LOG_GROUP_ID", 0) or 0)

    # ── Database ─────────────────────────────
    DATABASE_URL: str  = os.getenv("DATABASE_URL", "")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "MissCherryDB")

    # ── DeepSeek AI ──────────────────────────
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str   = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # ── Bot Info ─────────────────────────────
    BOT_NAME: str  = os.getenv("BOT_NAME", "Miss Cherry 🍒")
    START_IMG: str = os.getenv("START_IMG", "https://files.catbox.moe/8ft1s9.png")

    # ── Rich Messages (Bot API 10.3, needs Kurigram >= 2.2.26) ──
    RICH_BUTTONS: bool = os.getenv("RICH_BUTTONS", "on").strip().lower() not in ("0", "off", "no", "false")

    # ── Button icons (custom emoji ids, JSON) ─
    # e.g. BUTTON_ICONS={"close":"5310169226856644648","back":"5285430309720966085"}
    BUTTON_ICONS: dict = {}

    # ── Links ────────────────────────────────
    SUPPORT_LINK:       str = os.getenv("SUPPORT_LINK", "https://t.me/alfabots_support")
    UPDATE_LINK:        str = os.getenv("UPDATE_LINK", "https://t.me/Alfabots_update")
    SOURCE_LINK:        str = os.getenv("SOURCE_LINK", "https://t.me/uffsexyboi")
    DOCS_URL:           str = os.getenv("DOCS_URL", "https://precious-sunflower-cfe571.netlify.app/)
    OWNER_USERNAME:     str = os.getenv("OWNER_USERNAME", "@ll_cherruu")
    DEVELOPER_USERNAME: str = os.getenv("DEVELOPER_USERNAME", "@uffsexyboi")


def _load_icons() -> dict:
    try:
        data = json.loads(os.getenv("BUTTON_ICONS", "") or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


Config.BUTTON_ICONS = _load_icons()
cfg = Config()
