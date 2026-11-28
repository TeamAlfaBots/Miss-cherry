# ╔══════════════════════════════════════════╗
# ║      Miss Cherry - Chatbot Module        ║
# ║  DeepSeek AI + Hinglish dataset + owners ║
# ╚══════════════════════════════════════════╝
#
# Files used (all inside the /chatbot folder at the repo root):
#   chatbot/train.jsonl       Hinglish example chats  (retrieval + local replies)
#   chatbot/personality.json  Cherry's persona rules   (becomes the system prompt)
#   chatbot/owners.json       owners: how the bot talks to them (Sir/Boss/Mam)
#
# How a reply is made
#   1. Owner  -> special respectful prompt (no dataset examples, always "aap").
#   2. Others -> short greeting/bye: answered straight from the dataset (free, instant)
#                otherwise 3 similar dataset chats are put in the prompt as *style*
#                examples and DeepSeek writes the reply.
#   3. DeepSeek down / no key -> best dataset reply (owners get a polite message).

import asyncio
import json
import random
import re
import time
from pathlib import Path

import aiohttp
from pyrogram import Client, filters, enums
from pyrogram.types import Message

from core.compat import enum_name
from core.database import (
    set_chatbot, get_chatbot,
    get_chat_history, save_chat_history,
)
from core.filters import admin_filter
from core.logger import logger
from core.translator import _

DATA_DIR = Path(__file__).resolve().parent.parent / "chatbot"

# ── DeepSeek settings (hardcoded) ──────────────────────────────
# ⚠️ Is file me secret key hai — public GitHub repo me mat daalna (key leak ho jati hai).
DEEPSEEK_API_KEY = "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"
DEEPSEEK_BASE_URL = "https://api.groq.com/openai/v1"
DEEPSEEK_MODEL = "openai/gpt-oss-120b"


def _key_ready() -> bool:
    k = (DEEPSEEK_API_KEY or "").strip()
    return bool(k) and "PASTE_YOUR" not in k

USER_COOLDOWN = 3          # seconds between replies to the same normal user
HISTORY_SENT = 12          # last N messages sent to the model
EXAMPLES_K = 3             # dataset examples per request
MIN_SCORE = 0.3            # minimum word-overlap score for an example


# ══════════════════════════════════════════════
#  OWNERS  (chatbot/owners.json)
# ══════════════════════════════════════════════
def _load_owners():
    try:
        data = json.loads((DATA_DIR / "owners.json").read_text(encoding="utf-8"))
        owners = {int(o["id"]): o for o in data.get("owners", [])}
        return owners, bool(data.get("reply_to_all", False))
    except Exception as e:
        logger.warning(f"chatbot: owners.json not loaded ({e!r})")
        return {}, False


OWNERS, REPLY_TO_ALL = _load_owners()


def _owner_prompt(owner: dict, first_name: str) -> str:
    calls = owner.get("call") or ["Sir"]
    main = owner.get("role") == "main_owner"
    if owner.get("gender") == "female":
        text = (
            f"SPECIAL: Abhi tum apni OWNER se baat kar rahi ho (naam: {first_name}). "
            f"Unhe hamesha '{calls[0]}' bolo. Bahut izzat aur pyaar bhare, meethe aur caring andaaz me "
            "baat karo, 'aap' use karo ('tum' nahi). Kabhi kabhi 🌸 💖 🙏 jaise emojis chalenge. "
            "Ye izzat aur apnepan hai, romantic baat nahi."
        )
    else:
        alt = f" aur kabhi kabhi '{calls[1]}'" if len(calls) > 1 else ""
        text = (
            f"SPECIAL: Abhi tum apne{' MAIN' if main else ''} OWNER se baat kar rahi ho (naam: {first_name}). "
            f"Unhe hamesha '{calls[0]}'{alt} bolo. Bahut adab aur izzat se baat karo, 'aap' use karo "
            f"('tum' nahi). Jawab chhote aur seedhe rakho, 'Ji {calls[0]}' jaisa andaaz chalega."
        )
    text += (
        " Agar wo koi kaam bole jo tum sirf chat se nahi kar sakti (ban, promote, etc.), "
        "jhooth mat bolo ki kar diya — sahi command batao."
    )
    if owner.get("extra"):
        text += " " + owner["extra"]
    return text


def _owner_fallback(owner: dict, reason: str = "") -> str:
    call = (owner.get("call") or ["Sir"])[0]
    text = f"Ji {call}, abhi thodi technical dikkat aa gayi hai 🙏 thodi der baad phir try kijiye."
    if reason and owner.get("role") == "main_owner":      # debug info only for the main owner
        text += f"\n\n🛠 {reason}"
    return text


# ══════════════════════════════════════════════
#  DATASET  (chatbot/train.jsonl)
# ══════════════════════════════════════════════
_STOP = {"hai", "kya", "ho", "me", "ko", "ka", "ki", "ke", "se", "to", "toh", "aur", "or", "ye",
         "yaar", "mujhe", "mera", "main", "cherry", "miss", "hu", "hoon", "tum", "ek", "bhi", "na"}
_ALIAS = {"nhi": "nahi", "kr": "kar", "kro": "karo", "btao": "batao", "rha": "raha", "rhi": "rahi",
          "bnao": "banao", "hu": "hoon", "bht": "bahut", "pls": "please", "plz": "please"}


def _tok(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_ALIAS.get(w, w) for w in words if w not in _STOP}


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


class _Data:
    def __init__(self):
        self.ready = False
        self.rows: list = []          # (category, subcategory, messages)
        self.toks: list = []          # frozenset of user-word tokens per row
        self.index: dict = {}         # token -> [row ids]
        self.local: dict = {}         # normalized greeting/closing -> [replies]
        self._lock = asyncio.Lock()

    def _build(self):
        path = DATA_DIR / "train.jsonl"
        rows, toks, index, local = [], [], {}, {}
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                msgs = r.get("m") or []
                if len(msgs) < 2:
                    continue
                i = len(rows)
                user_text = " ".join(msgs[0::2])
                t = frozenset(_tok(user_text))
                rows.append((r.get("c", ""), r.get("s", ""), msgs))
                toks.append(t)
                for w in t:
                    index.setdefault(w, []).append(i)
                if r.get("c") in ("greeting", "closing"):
                    key = _norm(msgs[0])
                    if key and len(key.split()) <= 5:
                        local.setdefault(key, []).append(msgs[1])
        self.rows, self.toks, self.index, self.local = rows, toks, index, local
        logger.info(f"chatbot dataset loaded: {len(rows)} rows, {len(local)} local phrases")

    async def ensure(self):
        if self.ready:
            return
        async with self._lock:
            if self.ready:
                return
            try:
                await asyncio.to_thread(self._build)
            except Exception as e:
                logger.warning(f"chatbot: dataset not loaded ({e!r}) — running without it")
            self.ready = True

    def local_reply(self, text: str):
        key = _norm(text)
        if not key or len(key.split()) > 5:
            return None
        replies = self.local.get(key)
        return random.choice(replies) if replies else None

    def examples(self, text: str, k: int = EXAMPLES_K) -> list:
        """Most similar dataset chats (first exchange only), one per subcategory."""
        q = _tok(text)
        if not q or not self.rows:
            return []
        limit = len(self.rows) * 0.2       # ignore words that are in >20% of rows
        cand = set()
        for w in q:
            ids = self.index.get(w)
            if ids and len(ids) < limit:
                cand.update(ids)
        scored = []
        for i in cand:
            t = self.toks[i]
            inter = len(q & t)
            if inter:
                s = inter / len(q | t)
                if s >= MIN_SCORE:
                    scored.append((s, i))
        scored.sort(reverse=True)
        out, seen = [], set()
        for _s, i in scored:
            cat, sub, msgs = self.rows[i]
            if (cat, sub) in seen:
                continue
            seen.add((cat, sub))
            out.append((msgs[0], msgs[1]))
            if len(out) == k:
                break
        return out


DATA = _Data()


# ══════════════════════════════════════════════
#  PERSONA / PROMPT  (chatbot/personality.json)
# ══════════════════════════════════════════════
def _load_persona() -> str:
    try:
        p = json.loads((DATA_DIR / "personality.json").read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"chatbot: personality.json not loaded ({e!r})")
        p = {}
    def block(title, key):
        items = p.get(key) or []
        return f"{title}:\n" + "\n".join(f"- {x}" for x in items) if items else ""
    voice = p.get("voice", {})
    parts = [
        "Tum Miss Cherry 🍒 ho — ek friendly female-voice AI assistant aur Telegram group moderator bot. "
        "Natural Hinglish (Roman script) me baat karti ho; agar user pure English me likhe to English me jawab do.",
        f"Voice: {voice.get('gender_grammar', '')}. User ko {', '.join(voice.get('address_user_as', []))} bol sakti ho; "
        f"{', '.join(voice.get('avoid_address', []))} mat bolo.",
        block("Tone", "tone"),
        block("Style rules", "style_rules"),
        block("Identity rules", "identity_rules"),
        block("Natural chat rules", "natural_chat_rules"),
        block("Avoid", "avoid"),
        "Messages '[Naam]: text' format me aate hain — Naam bolne waale ka hai. Apne jawab me '[Naam]:' "
        "likhna nahi; naam kabhi kabhi hi use karo. Jawab 1-3 chhote sentences me do.",
    ]
    return "\n\n".join(x for x in parts if x)


PERSONA = _load_persona()


def build_system(examples: list, owner: dict = None, first_name: str = "") -> str:
    system = PERSONA
    if owner:
        system += "\n\n" + _owner_prompt(owner, first_name or "Owner")
    elif examples:
        shots = "\n\n".join(f"User: {u}\nCherry: {a}" for u, a in examples)
        system += (
            "\n\nStyle ke examples (sirf andaaz/tone samajhne ke liye — inhe apni yaad ya fact "
            "mat samajhna, copy mat karo):\n" + shots
        )
    return system


# ══════════════════════════════════════════════
#  DEEPSEEK
# ══════════════════════════════════════════════
_session: aiohttp.ClientSession = None


async def _call_deepseek(system: str, history: list) -> str:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "system", "content": system}] + history[-HISTORY_SENT:],
        "max_tokens": 200,
        "temperature": 0.8,
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY.strip()}",
        "Content-Type": "application/json",
    }
    async with _session.post(
        f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
        json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        status = resp.status
        body = await resp.text()
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {body[:150]}")
    try:
        text = json.loads(body)["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"Bad response: {body[:150]}")
    if not (text or "").strip():
        raise RuntimeError("Empty reply from DeepSeek")
    return text


def _clean(reply: str) -> str:
    reply = re.sub(r"^\s*\[[^\]\n]{1,40}\]\s*:\s*", "", (reply or "").strip())
    return reply[:1000].strip()


async def generate_reply(history: list, text: str, first_name: str, owner: dict = None):
    """Returns (reply, updated_history)."""
    await DATA.ensure()
    msg = f"[{first_name}]: {text}"

    # 1. free instant reply for short greetings / goodbyes (never for owners)
    if not owner:
        local = DATA.local_reply(text)
        if local:
            return local, history + [{"role": "user", "content": msg},
                                     {"role": "assistant", "content": local}]

    history = history + [{"role": "user", "content": msg}]

    # 2. DeepSeek with persona (+ dataset style examples for normal users)
    reply, reason = "", ""
    if not _key_ready():
        reason = "DEEPSEEK_API_KEY set nahi hai (modules/chatbot.py me upar daalo)"
        logger.warning(f"chatbot: {reason}")
    else:
        try:
            examples = [] if owner else DATA.examples(text)
            reply = _clean(await _call_deepseek(build_system(examples, owner, first_name), history))
        except Exception as e:
            reason = str(e)[:160] or repr(e)
            logger.warning(f"chatbot: DeepSeek failed: {reason}")

    # 3. fallback
    if not reply:
        if owner:
            reply = _owner_fallback(owner, reason)
        else:
            best = DATA.examples(text, 1)
            reply = best[0][1] if best else "Abhi thoda issue aa gaya yaar 😅 thodi der baad try karo."
            # DeepSeek problem must not poison the saved history
            history = history[:-1]
            return reply, history + [{"role": "user", "content": msg},
                                     {"role": "assistant", "content": reply}]

    return reply, history + [{"role": "assistant", "content": reply}]


# ══════════════════════════════════════════════
#  HANDLERS
# ══════════════════════════════════════════════
@Client.on_message(filters.command("chatbot") & ~filters.private & admin_filter)
async def cmd_chatbot(client: Client, message: Message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        status = await get_chatbot(message.chat.id)
        key = "chatbot.status_on" if status else "chatbot.status_off"
        return await message.reply(await _(message.chat.id, key))
    val = args[1].lower() in ("on",)
    await set_chatbot(message.chat.id, val)
    key = "chatbot.on" if val else "chatbot.off"
    await message.reply(await _(message.chat.id, key))


_last_reply: dict = {}


def _addressed(client_me, message: Message) -> bool:
    """Old rules: direct group message, reply to the bot, or bot mentioned."""
    has_mention = bool(message.entities and any(
        e.type == enums.MessageEntityType.MENTION for e in message.entities))
    is_direct = message.reply_to_message is None and not has_mention
    rep = message.reply_to_message
    is_reply_bot = bool(rep and rep.from_user and rep.from_user.id == client_me.id)
    is_mentioned = bool(client_me.username and
                        f"@{client_me.username}".lower() in (message.text or "").lower())
    return is_direct or is_reply_bot or is_mentioned


def _mentioned_or_replied(client_me, message: Message) -> bool:
    """Strict check used for owners in groups: the bot must be @mentioned,
    or the message must be a reply to one of the bot's own messages."""
    rep = message.reply_to_message
    if rep and rep.from_user and rep.from_user.id == client_me.id:
        return True
    return bool(client_me.username and
                f"@{client_me.username}".lower() in (message.text or "").lower())


@Client.on_message(filters.text & ~filters.service & ~filters.regex(r"^/"), group=13)
async def chatbot_handler(client: Client, message: Message):
    user = message.from_user
    if not user or user.is_bot or not message.text:
        return
    owner = OWNERS.get(user.id)
    is_private = enum_name(message.chat.type) == "private"

    if is_private:
        if not owner:                      # DMs: only owners are answered
            return
    else:
        me = client.me or await client.get_me()
        if owner:
            # owners are answered even when the chatbot is OFF in this group,
            # but (default) only on @mention or reply-to-bot — not every message
            if not REPLY_TO_ALL and not _mentioned_or_replied(me, message):
                return
        else:
            if not await get_chatbot(message.chat.id):
                return
            if not _addressed(me, message):
                return

    if not owner:                          # light anti-spam for normal users
        key = (message.chat.id, user.id)
        now = time.monotonic()
        last = _last_reply.get(key)
        if last is not None and now - last < USER_COOLDOWN:
            return
        _last_reply[key] = now
        if len(_last_reply) > 20000:
            _last_reply.clear()

    history = await get_chat_history(message.chat.id, user.id)
    reply, updated = await generate_reply(history, message.text, user.first_name or "User", owner)
    await save_chat_history(message.chat.id, user.id, updated)
    try:
        await message.reply(reply, parse_mode=enums.ParseMode.DISABLED)
    except Exception:
        pass
        
