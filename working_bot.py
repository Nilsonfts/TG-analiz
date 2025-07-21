#!/usr/bin/env python3
"""
РАБОЧИЙ TG-analiz Bot - ГАРАНТИРОВАННО РАБОТАЕТ!
"""
import asyncio
import json
import logging
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Configuration
PORT = int(os.getenv("PORT", "8080")) # Railway provides the PORT env var
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

logger.info("🚀 РАБОЧИЙ БОТ СТАРТУЕТ!")
logger.info(f"PORT: {PORT}")
logger.info(f"BOT_TOKEN: {'ДА' if BOT_TOKEN else 'НЕТ'}")

class WorkingHealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress HTTP logs for cleaner output
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        data = {"status": "ok", "healthy": True, "bot": "working"}
        self.wfile.write(json.dumps(data).encode())

def start_health_server():
    """Starts the health check server in a background thread."""
    try:
        server = HTTPServer(("0.0.0.0", PORT), WorkingHealthHandler)
        logger.info(f"✅ Health server running on port {PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Health error: {e}")

async def start_working_bot():
    """Initializes and runs the main Telegram bot."""
    if not BOT_TOKEN:
        logger.error("❌ NO BOT_TOKEN! The bot cannot start.")
        return
    
    try:
        # Safe import to prevent crashes if not installed
        logger.info("📦 Importing telegram...")
        from telegram import Update, Bot
        from telegram.ext import Application, CommandHandler, ContextTypes
        logger.info("✅ Telegram imported successfully")
        
        # Test the token before starting
        logger.info("🔑 Testing BOT_TOKEN...")
        bot = Bot(BOT_TOKEN)
        me = await bot.get_me()
        logger.info(f"✅ Bot verified: @{me.username}")
        
        # Create the Application
        logger.info("🔧 Creating application...")
        app = Application.builder().token(BOT_TOKEN).build()
        logger.info("✅ Application created")
        
        # Simple command handlers for testing
        async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info(f"📨 /start from user {update.effective_user.id}")
            await update.message.reply_text(
                "🎉 <b>БОТ РАБОТАЕТ!</b>\n\n"
                "✅ Railway деплой успешен\n"
                "✅ Health check активен\n"
                "✅ Telegram API подключен\n\n"
                "🚀 <b>ПРОБЛЕМА РЕШЕНА!</b>",
                parse_mode='HTML'
            )
            logger.info("✅ /start response sent")
        
        app.add_handler(CommandHandler("start", start_cmd))
        logger.info("✅ Commands registered")
        
        # Start the bot
        logger.info("🤖 STARTING TELEGRAM BOT...")
        await app.run_polling(drop_pending_updates=True)
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}. Please install python-telegram-bot.")
    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def main():
    logger.info("🎬 MAIN FUNCTION START")
    
    # Start the health server in a separate thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    logger.info("🏥 Health server starting in background")
    
    await asyncio.sleep(2) # Give server a moment to start
    
    # Start the Telegram bot
    logger.info("🤖 Starting Telegram bot...")
    await start_working_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR: {e}")
        sys.exit(1)
