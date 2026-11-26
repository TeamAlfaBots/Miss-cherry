# ╔══════════════════════════════════════════╗
# ║       Miss Cherry - Database             ║
# ╚══════════════════════════════════════════╝

import time

from motor.motor_asyncio import AsyncIOMotorClient
from core.config import cfg
from core.logger import logger


# ══════════════════════════════════════════════
#  IN-MEMORY TTL CACHE
#  Hot read paths (every message hits sudo / language / flood /
#  blocklist / filters / approved ...) are served from memory.
#  Every setter below invalidates its own key, and the TTL is only a
#  safety net.  Cached values are never mutated by callers (copies are
#  returned for dict / list values).
# ══════════════════════════════════════════════
_MISS = object()
_CACHE: dict = {}
_TTL = 60          # seconds
_MAX_ENTRIES = 50000


def _cget(ns: str, key):
    hit = _CACHE.get((ns, key))
    if hit is not None and time.monotonic() - hit[1] < _TTL:
        v = hit[0]
        if isinstance(v, dict):
            return dict(v)
        if isinstance(v, list):
            return list(v)
        return v
    return _MISS


def _cput(ns: str, key, value):
    if len(_CACHE) > _MAX_ENTRIES:
        _CACHE.clear()
    _CACHE[(ns, key)] = (value, time.monotonic())
    return value


def _cdrop(ns: str, key=None):
    """Drop one key, or the whole namespace when key is None."""
    if key is not None:
        _CACHE.pop((ns, key), None)
        return
    for k in [k for k in _CACHE if k[0] == ns]:
        _CACHE.pop(k, None)


def _cdrop_chat(ns: str, chat_id: int):
    """Drop every (chat_id, ...) tuple-key of a namespace."""
    for k in [k for k in _CACHE
              if k[0] == ns and isinstance(k[1], tuple) and k[1] and k[1][0] == chat_id]:
        _CACHE.pop(k, None)


class Database:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect(self):
        self.client = AsyncIOMotorClient(cfg.DATABASE_URL)
        self.db = self.client[cfg.DATABASE_NAME]
        logger.info("MongoDB connected!")
        await self._ensure_indexes()

    async def _ensure_indexes(self):
        """Indexes for the (chat_id, user_id / trigger) lookups."""
        specs = {
            "warns":           [("chat_id", 1), ("user_id", 1)],
            "approved":        [("chat_id", 1), ("user_id", 1)],
            "filters":         [("chat_id", 1), ("trigger", 1)],
            "blocklist":       [("chat_id", 1), ("trigger", 1)],
            "chatbot_history": [("chat_id", 1), ("user_id", 1)],
        }
        for coll, keys in specs.items():
            try:
                await self.db[coll].create_index(keys)
            except Exception as e:
                logger.warning(f"Index create failed for {coll}: {e}")

    async def close(self):
        if self.client:
            self.client.close()

    def __getattr__(self, name):
        return self.db[name]


db = Database()


# ══════════════════════════════════════════════
#  SUDO
# ══════════════════════════════════════════════
async def add_sudo(user_id: int):
    await db.sudos.update_one({"_id": user_id}, {"$set": {"_id": user_id}}, upsert=True)
    _cdrop("sudo", "all")

async def remove_sudo(user_id: int):
    await db.sudos.delete_one({"_id": user_id})
    _cdrop("sudo", "all")

async def get_sudos() -> list:
    hit = _cget("sudo", "all")
    if hit is not _MISS:
        return hit
    return list(_cput("sudo", "all", [d["_id"] async for d in db.sudos.find()]))


# ══════════════════════════════════════════════
#  CHATS & USERS
# ══════════════════════════════════════════════
async def save_chat(chat_id: int, title: str, ctype: str = None):
    """Save / refresh a chat and mark it active (bot is in it)."""
    data = {"title": title, "active": True}
    if ctype:
        data["type"] = ctype
    await db.chats.update_one({"_id": chat_id}, {"$set": data}, upsert=True)

async def set_chat_active(chat_id: int, active: bool):
    """Mark a chat inactive when the bot was removed (settings are kept)."""
    await db.chats.update_one({"_id": chat_id}, {"$set": {"active": active}}, upsert=True)

async def save_user(user_id: int, username: str = None):
    await db.users.update_one({"_id": user_id}, {"$set": {"username": username}}, upsert=True)

async def get_all_chats() -> list:
    return [d async for d in db.chats.find({"active": {"$ne": False}})]

async def get_all_users() -> list:
    return [d async for d in db.users.find()]


# ══════════════════════════════════════════════
#  LANGUAGE
# ══════════════════════════════════════════════
async def set_language(chat_id: int, lang: str):
    await db.language.update_one({"_id": chat_id}, {"$set": {"lang": lang}}, upsert=True)
    _cdrop("lang", chat_id)

async def get_language(chat_id: int) -> str:
    hit = _cget("lang", chat_id)
    if hit is not _MISS:
        return hit
    doc = await db.language.find_one({"_id": chat_id})
    return _cput("lang", chat_id, doc["lang"] if doc else "en")


# ══════════════════════════════════════════════
#  ANTIFLOOD
# ══════════════════════════════════════════════
async def set_flood(chat_id: int, limit: int):
    await db.antiflood.update_one({"_id": chat_id}, {"$set": {"limit": limit}}, upsert=True)
    _cdrop("flood", chat_id)

async def get_flood(chat_id: int) -> dict:
    hit = _cget("flood", chat_id)
    if hit is not _MISS:
        return hit
    return dict(_cput("flood", chat_id, await db.antiflood.find_one({"_id": chat_id}) or {}))

async def set_flood_mode(chat_id: int, mode: str):
    await db.antiflood.update_one({"_id": chat_id}, {"$set": {"mode": mode}}, upsert=True)
    _cdrop("flood", chat_id)

async def set_flood_timer(chat_id: int, count: int, duration: int):
    await db.antiflood.update_one({"_id": chat_id}, {"$set": {"timer_count": count, "timer_duration": duration}}, upsert=True)
    _cdrop("flood", chat_id)

async def set_clear_flood(chat_id: int, value: bool):
    await db.antiflood.update_one({"_id": chat_id}, {"$set": {"clear": value}}, upsert=True)
    _cdrop("flood", chat_id)


# ══════════════════════════════════════════════
#  ANTIRAID
# ══════════════════════════════════════════════
async def set_antiraid(chat_id: int, status: bool, duration: int = 21600):
    # "until" = absolute unix time when antiraid switches itself off
    until = time.time() + duration if status else 0
    await db.antiraid.update_one(
        {"_id": chat_id},
        {"$set": {"enabled": status, "duration": duration, "until": until}},
        upsert=True,
    )
    _cdrop("antiraid", chat_id)

async def get_antiraid(chat_id: int) -> dict:
    hit = _cget("antiraid", chat_id)
    if hit is not _MISS:
        return hit
    return dict(_cput("antiraid", chat_id, await db.antiraid.find_one({"_id": chat_id}) or {}))

async def set_raidtime(chat_id: int, seconds: int):
    await db.antiraid.update_one({"_id": chat_id}, {"$set": {"raidtime": seconds}}, upsert=True)
    _cdrop("antiraid", chat_id)

async def set_raidactiontime(chat_id: int, seconds: int):
    await db.antiraid.update_one({"_id": chat_id}, {"$set": {"actiontime": seconds}}, upsert=True)
    _cdrop("antiraid", chat_id)

async def set_autoantiraid(chat_id: int, joins: int):
    await db.antiraid.update_one({"_id": chat_id}, {"$set": {"auto_joins": joins}}, upsert=True)
    _cdrop("antiraid", chat_id)


# ══════════════════════════════════════════════
#  APPROVED
# ══════════════════════════════════════════════
async def approve_user(chat_id: int, user_id: int):
    await db.approved.update_one({"chat_id": chat_id, "user_id": user_id}, {"$set": {"chat_id": chat_id, "user_id": user_id}}, upsert=True)
    _cdrop("approved", (chat_id, user_id))

async def unapprove_user(chat_id: int, user_id: int):
    await db.approved.delete_one({"chat_id": chat_id, "user_id": user_id})
    _cdrop("approved", (chat_id, user_id))

async def is_approved(chat_id: int, user_id: int) -> bool:
    key = (chat_id, user_id)
    hit = _cget("approved", key)
    if hit is not _MISS:
        return hit
    return _cput("approved", key, bool(await db.approved.find_one({"chat_id": chat_id, "user_id": user_id})))

async def get_approved_users(chat_id: int) -> list:
    return [d["user_id"] async for d in db.approved.find({"chat_id": chat_id})]

async def unapprove_all(chat_id: int):
    await db.approved.delete_many({"chat_id": chat_id})
    _cdrop_chat("approved", chat_id)


# ══════════════════════════════════════════════
#  BLOCKLIST
# ══════════════════════════════════════════════
async def add_blocklist(chat_id: int, trigger: str, reason: str = ""):
    await db.blocklist.update_one({"chat_id": chat_id, "trigger": trigger}, {"$set": {"reason": reason}}, upsert=True)
    _cdrop("blocklist", chat_id)

async def remove_blocklist(chat_id: int, trigger: str):
    await db.blocklist.delete_one({"chat_id": chat_id, "trigger": trigger})
    _cdrop("blocklist", chat_id)

async def get_blocklist(chat_id: int) -> list:
    hit = _cget("blocklist", chat_id)
    if hit is not _MISS:
        return hit
    return list(_cput("blocklist", chat_id, [d async for d in db.blocklist.find({"chat_id": chat_id})]))

async def clear_blocklist(chat_id: int):
    await db.blocklist.delete_many({"chat_id": chat_id})
    _cdrop("blocklist", chat_id)

async def get_chat_settings(chat_id: int) -> dict:
    hit = _cget("settings", chat_id)
    if hit is not _MISS:
        return hit
    return dict(_cput("settings", chat_id, await db.chats.find_one({"_id": chat_id}) or {}))

async def set_chat_setting(chat_id: int, key: str, value):
    await db.chats.update_one({"_id": chat_id}, {"$set": {key: value}}, upsert=True)
    _cdrop("settings", chat_id)


# ══════════════════════════════════════════════
#  FILTERS
# ══════════════════════════════════════════════
async def add_filter(chat_id: int, trigger: str, reply: str):
    await db.filters.update_one({"chat_id": chat_id, "trigger": trigger}, {"$set": {"reply": reply}}, upsert=True)
    _cdrop("filters", chat_id)

async def remove_filter(chat_id: int, trigger: str):
    await db.filters.delete_one({"chat_id": chat_id, "trigger": trigger})
    _cdrop("filters", chat_id)

async def get_filters(chat_id: int) -> list:
    hit = _cget("filters", chat_id)
    if hit is not _MISS:
        return hit
    return list(_cput("filters", chat_id, [d async for d in db.filters.find({"chat_id": chat_id})]))

async def clear_filters(chat_id: int):
    await db.filters.delete_many({"chat_id": chat_id})
    _cdrop("filters", chat_id)


# ══════════════════════════════════════════════
#  GREETINGS
# ══════════════════════════════════════════════
async def set_greeting(chat_id: int, key: str, value):
    await db.greetings.update_one({"_id": chat_id}, {"$set": {key: value}}, upsert=True)
    _cdrop("greet", chat_id)

async def get_greeting(chat_id: int) -> dict:
    hit = _cget("greet", chat_id)
    if hit is not _MISS:
        return hit
    return dict(_cput("greet", chat_id, await db.greetings.find_one({"_id": chat_id}) or {}))


# ══════════════════════════════════════════════
#  RULES
# ══════════════════════════════════════════════
async def set_rules(chat_id: int, text: str):
    await db.rules.update_one({"_id": chat_id}, {"$set": {"text": text}}, upsert=True)

async def get_rules(chat_id: int) -> dict:
    return await db.rules.find_one({"_id": chat_id}) or {}

async def reset_rules(chat_id: int):
    await db.rules.delete_one({"_id": chat_id})


# ══════════════════════════════════════════════
#  WARNINGS
# ══════════════════════════════════════════════
def _warn_reason(w) -> str:
    return w["r"] if isinstance(w, dict) else w


async def _live_warns(chat_id: int, user_id: int):
    """Return (doc, warns) with expired warns (per /warntime) removed."""
    import time
    from utils.time_parser import parse_time
    doc = await db.warns.find_one({"chat_id": chat_id, "user_id": user_id})
    warns = doc.get("warns", []) if doc else []
    expiry = parse_time((await get_chat_settings(chat_id)).get("warn_time") or "")
    if expiry:
        now = time.time()
        warns = [w for w in warns if not isinstance(w, dict) or now - w.get("t", now) < expiry]
    return doc, warns


async def add_warn(chat_id: int, user_id: int, reason: str) -> int:
    import time
    _doc, warns = await _live_warns(chat_id, user_id)
    warns.append({"r": reason, "t": time.time()})
    await db.warns.update_one({"chat_id": chat_id, "user_id": user_id}, {"$set": {"warns": warns}}, upsert=True)
    return len(warns)

async def get_warns(chat_id: int, user_id: int) -> list:
    _doc, warns = await _live_warns(chat_id, user_id)
    return [_warn_reason(w) for w in warns]

async def remove_last_warn(chat_id: int, user_id: int):
    _doc, warns = await _live_warns(chat_id, user_id)
    if warns:
        warns.pop()
        await db.warns.update_one({"chat_id": chat_id, "user_id": user_id}, {"$set": {"warns": warns}})

async def reset_warns(chat_id: int, user_id: int):
    await db.warns.delete_one({"chat_id": chat_id, "user_id": user_id})

async def reset_all_warns(chat_id: int):
    await db.warns.delete_many({"chat_id": chat_id})

async def get_warn_settings(chat_id: int) -> dict:
    doc = await get_chat_settings(chat_id)
    return {
        "limit": doc.get("warn_limit", 3),
        "mode":  doc.get("warn_mode", "ban"),
        "time":  doc.get("warn_time", None)
    }


# ══════════════════════════════════════════════
#  CHATBOT
# ══════════════════════════════════════════════
async def set_chatbot(chat_id: int, status: bool):
    await db.chatbot.update_one({"_id": chat_id}, {"$set": {"enabled": status}}, upsert=True)
    _cdrop("chatbot", chat_id)

async def get_chatbot(chat_id: int) -> bool:
    hit = _cget("chatbot", chat_id)
    if hit is not _MISS:
        return hit
    doc = await db.chatbot.find_one({"_id": chat_id})
    return _cput("chatbot", chat_id, doc.get("enabled", False) if doc else False)

async def get_chat_history(chat_id: int, user_id: int) -> list:
    doc = await db.chatbot_history.find_one({"chat_id": chat_id, "user_id": user_id})
    return doc.get("history", []) if doc else []

async def save_chat_history(chat_id: int, user_id: int, history: list):
    history = history[-20:]
    await db.chatbot_history.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"history": history}},
        upsert=True
    )
