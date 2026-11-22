# ╔══════════════════════════════════════════╗
# ║         Miss Cherry 🍒 Bot               ║
# ║         Made by AlfaBots                 ║
# ╚══════════════════════════════════════════╝

import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from pyrogram import Client, idle
from pyrogram.enums import ParseMode

from core.config import cfg
from core.logger import logger
from core.database import db
from core.translator import load_locales

plugins = dict(root="modules")

app: Client = None


# HTTP Server for Render health checks
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Miss Cherry is running')

    def log_message(self, format, *args):
        pass  # Suppress logs


def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"✅ HTTP health check server started on port {port}")
    server.serve_forever()


async def main():
    global app

    missing = [k for k in ("BOT_TOKEN", "API_HASH", "DATABASE_URL") if not getattr(cfg, k)]
    if not cfg.API_ID:
        missing.append("API_ID")
    if missing:
        raise SystemExit(f"❌ Missing config: {', '.join(missing)} (fill .env / env vars)")

    # Start HTTP server in background thread (keeps Render alive)
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    logger.info("HTTP server thread started for Render health checks")

    app = Client(
        "MissCherry",
        api_id=cfg.API_ID,
        api_hash=cfg.API_HASH,
        bot_token=cfg.BOT_TOKEN,
        plugins=plugins,
        parse_mode=ParseMode.HTML
    )

    await db.connect()
    logger.info("✅ Database connected")

    load_locales()
    logger.info("✅ Locales loaded")

    await app.start()
    me = await app.get_me()
    logger.info(f"✅ Bot started as @{me.username}")
    from utils.rich import RICH_AVAILABLE, rich_enabled
    logger.info(f"Rich Message buttons (Bot API 10.3): "
                f"{'ON' if rich_enabled() else 'OFF'} (kurigram support: {RICH_AVAILABLE})")

    await idle()

    await app.stop()
    await db.close()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    print("╔══════════════════════════════════╗")
    print("║   Miss Cherry 🍒 Bot Starting... ║")
    print("║         By AlfaBots              ║")
    print("╚══════════════════════════════════╝")

    asyncio.run(main())
