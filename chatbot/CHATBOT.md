# 🤖 Miss Cherry — Chatbot Logic

How the chatbot in `modules/chatbot.py` decides **when** to reply, **who** it is talking to, and **what** it says.

---

## 1. Files

```
repo-root/
├── modules/
│   └── chatbot.py            ← all logic (handlers, retrieval, prompt, DeepSeek call)
└── chatbot/                  ← data folder (read by chatbot.py)
    ├── train.jsonl           ← Hinglish example chats (16,509 rows, ~4 MB)
    ├── personality.json      ← Cherry's persona rules → become the system prompt
    └── owners.json           ← owners: ids, how to address them, reply mode
```

Edit the files in `chatbot/` to change behaviour — no code change needed.

---

## 2. Big picture

```
Message arrives (text, not a /command)
        │
        ▼
 Who is the sender?
   ├─ Owner (owners.json) ──► owner prompt (Sir / Boss / Mam, "aap")
   │                          no dataset examples, no local reply
   └─ Normal user ──────────► chatbot must be ON + bot must be addressed
                              + 3 s cooldown
        │
        ▼
 Short greeting / goodbye?  (normal users only)
   ├─ yes ─► reply straight from dataset (free, instant, no DeepSeek)
   └─ no  ─► build system prompt
                = persona (personality.json)
                + owner block   (owners)   OR   3 similar dataset chats (normal users)
             call DeepSeek with last 12 messages
        │
        ▼
 DeepSeek failed / no API key?
   ├─ owner  ─► "Ji Sir/Mam, abhi thodi technical dikkat aa gayi hai 🙏 ..."
   └─ others ─► best matching dataset reply (or a short generic line)
        │
        ▼
 Clean reply → send → save history in MongoDB
```

---

## 3. When does the bot reply?

Handler: `chatbot_handler` — group `13`, text messages only, ignores service messages and anything starting with `/`.

| Sender | Where | Condition |
|---|---|---|
| Any bot / no user | anywhere | ❌ ignored |
| **Owner** | private chat (DM) | ✅ always |
| **Owner** | group | ✅ even if chatbot is **OFF**. With `reply_to_all: true` → every message. With `false` → only when addressed |
| Normal user | private chat | ❌ ignored |
| Normal user | group | ✅ only if `/chatbot on` **and** addressed **and** 3 s since last reply |

**"Addressed"** means one of:
1. a direct group message (not a reply to someone, no @mention of another user),
2. a reply to the bot's message,
3. the bot's @username is in the text.

Replying to another human, or tagging someone else, keeps the bot silent (for normal users).

**Order of modules:** `owner_chat.py` (group −3, "Hello cherry" / "make me admin") runs first and stops propagation, so those messages never reach the chatbot.

### Commands
- `/chatbot on` / `/chatbot off` — group admins only (default: off).
- `/chatbot` — shows current status.

---

## 4. Owners (`chatbot/owners.json`)

```json
{
  "reply_to_all": true,
  "owners": [
    { "id": 7185778863, "role": "main_owner", "gender": "male",   "call": ["Sir", "Boss"], "extra": "" },
    { "id": 8556154047, "role": "owner",      "gender": "female", "call": ["Mam"],         "extra": "" },
    { "id": 8661302468, "role": "owner",      "gender": "male",   "call": ["Sir"],         "extra": "" }
  ]
}
```

| Field | Meaning |
|---|---|
| `id` | Telegram user id |
| `role` | `main_owner` → bot treats as the MAIN owner |
| `gender` | `female` → very respectful **and** warm/caring tone ("Mam", 🌸💖🙏). `male` → respectful, short, "Ji Sir" style |
| `call` | titles. First one is always used, the second ("Boss") only sometimes |
| `extra` | optional extra instruction added to the prompt for that owner |
| `reply_to_all` | `true` = answer every owner message. `false` = only when addressed |

Owner rules built into the prompt:
- always **"aap"**, never "tum";
- short, direct answers;
- if an owner asks for something chat can't do (ban, promote…), the bot must **not** pretend it was done — it names the right command;
- warm tone for the female owner is respect + affection, **not** a romantic role.

> Owners don't get dataset examples because the dataset speaks in a casual "tum" style.

**Add an owner:** add one object to `owners` and redeploy.

---

## 5. Dataset (`chatbot/train.jsonl`)

### Format (compact, one JSON per line)
```json
{"c":"empathy","s":"flow_reason","m":["Mann nhi lag rha","Hmm, kya hua yaar? ...","Bas Job nhi mil rhi na","Ye wait bahut thakaane wala hota hai. ..."]}
```
`c` = category, `s` = subcategory, `m` = messages in order: user, assistant, user, assistant …

### Cleaning done on the original "Lisa" dataset
- **Lisa → Cherry** everywhere (assistant lines and user lines).
- Removed the `writing` category (1,557 rows): those were drafts in the *user's* voice and "ek aur / shorter" follow-ups that make no sense without context.
- Removed 5,688 duplicate rows (same assistant reply). Greeting/closing rows keep distinct user phrases.
- Result: **16,509 rows**, 4.2 MB. Mostly `casual_chat`, `tech`, `study`, `empathy`, `greeting`.

### Loading
Loaded once, on the first message, in a background thread (`asyncio.to_thread`) so the bot never freezes. If the file is missing, the bot keeps working without it.

### Two ways the dataset is used

**A) Local replies (free, instant)**
Only for **greeting** and **closing** rows whose first user message is ≤ 5 words (131 phrases, e.g. "hi", "hello", "bye", "thanks yaar"). If the user's whole message matches one of them (lower-case, punctuation ignored), the bot picks a random stored reply — no DeepSeek call, no cost.

**B) Style examples for DeepSeek (retrieval)**
1. Tokenise the message: lower-case words, small stop-word list (`hai, kya, ho, ke …`) and spelling aliases (`nhi→nahi, kr→kar, btao→batao, rha→raha …`).
2. An inverted index (`word → row ids`) finds candidate rows. Words present in more than 20 % of rows are ignored.
3. Score = Jaccard overlap between the message words and the row's user words. Needs **≥ 0.3** (`MIN_SCORE`).
4. Up to **3** examples (`EXAMPLES_K`), only one per (category, subcategory), first exchange only.
5. They are written into the system prompt as *style examples only* ("don't treat as facts, don't copy").

If nothing scores high enough, no examples are added — better none than irrelevant ones.

---

## 6. Prompt building

`build_system()` = persona **+** one of:
- owner block (`_owner_prompt`) for owners, or
- the retrieved style examples for normal users.

Persona text comes from `personality.json`:

| Key | Used for |
|---|---|
| `voice` | feminine Hinglish grammar, how to address users (yaar / dost / tum), words to avoid (bhai, bro, baby, jaan) |
| `tone` | warm, friendly, slightly playful, calm when user is upset, honest |
| `style_rules` | short replies, ≤ 1 question, emojis only sometimes, live-data rule, tech answers |
| `identity_rules` | Cherry is an **AI**, no body/age/city/memories, **no girlfriend/romantic role**, no jealousy/guilt |
| `natural_chat_rules` | react first, refer back to earlier details, vary openers |
| `avoid` | flattery, invented memories, romantic/sexual roleplay, claiming real-time knowledge |
| *(code)* | messages arrive as `[Name]: text`; don't write `[Name]:` in the reply; reply in 1–3 short sentences |

Distress / self-harm handling comes from `style_rules` (warm, never agree giving up makes sense, point to a trusted person or helpline).

---

## 7. DeepSeek call

| Setting | Value |
|---|---|
| Endpoint | `https://api.deepseek.com/v1/chat/completions` |
| Model | `DEEPSEEK_MODEL` env (default `deepseek-chat`) |
| Key | `DEEPSEEK_API_KEY` env |
| `max_tokens` | 200 |
| `temperature` | 0.8 |
| Timeout | 30 s |
| Messages sent | system prompt + **last 12** history messages |
| HTTP session | one shared `aiohttp` session |

After the answer: a leading `[Name]:` is stripped and the reply is cut to 1,000 characters. Sent with parse mode **disabled** (no HTML/Markdown surprises).

---

## 8. Memory / history

- Per **(chat, user)** pair, stored in MongoDB `chatbot_history`.
- Each user line is saved as `[FirstName]: text`; assistant lines as plain text.
- Only the **last 20** messages are kept in the DB; **12** go to the model.
- Local (dataset) replies are also saved, so later answers have context.
- When DeepSeek fails for a normal user, the fallback reply is saved but the failed attempt is not repeated in history.

---

## 9. Fallbacks

| Situation | Result |
|---|---|
| No `DEEPSEEK_API_KEY` | same as a failed call |
| DeepSeek error / timeout / bad response | owners: *"Ji Sir/Mam, abhi thodi technical dikkat aa gayi hai 🙏 thodi der baad phir try kijiye."* · others: best dataset reply, or *"Abhi thoda issue aa gaya yaar 😅 thodi der baad try karo."* |
| `train.jsonl` missing | bot runs without examples / local replies |
| `personality.json` missing | persona is empty (warning in logs) — keep the file! |
| `owners.json` missing | no owners recognised (warning in logs) |

Errors are only logged — raw error text is **never** shown to users.

---

## 10. Tunable constants (top of `chatbot.py`)

| Constant | Default | Effect |
|---|---|---|
| `USER_COOLDOWN` | 3 s | min gap between replies to the same normal user (owners exempt) |
| `HISTORY_SENT` | 12 | messages sent to the model |
| `EXAMPLES_K` | 3 | dataset examples per request |
| `MIN_SCORE` | 0.3 | higher = fewer but more relevant examples |

---

## 11. How to extend

**Add your own greeting / bye replies**
Append a line to `chatbot/train.jsonl`:
```json
{"c":"greeting","s":"custom","m":["good morning","Good morning! Chai pi ya abhi bhi neend me ho? 😄"]}
```
Single-message user text of ≤ 5 words in category `greeting` or `closing` becomes a free local reply.

**Teach a topic**
Add rows with the right category (`tech`, `study`, `casual_chat` …). Several rows with similar user wording and different replies give variety.

**Change personality**
Edit `personality.json` lists (`style_rules`, `tone` …). Restart the bot.

**Change how owners are addressed**
Edit `call`, `gender` or `extra` in `owners.json`.

---

## 12. Limits & notes

- Dataset is **synthetic** (generated), so some replies repeat. Retrieval only picks *style*, DeepSeek writes the real answer.
- Retrieval is word-overlap based (no embeddings): good for Hinglish keywords, weak for very short or very unusual messages.
- In groups Telegram **privacy mode** hides normal text from bots that are not admins. Make the bot admin (or disable privacy in BotFather) or it will never see the messages.
- If an owner posts as an **anonymous admin**, the bot can't see their user id and won't treat them as an owner.
- Chat history is per user per group — it is not shared across groups.
