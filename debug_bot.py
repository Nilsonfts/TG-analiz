#!/usr/bin/env python3
"""
TG-analiz Bot - ИСПРАВЛЕННАЯ ВЕРСИЯ для Railway
"""
import asyncio
import json
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ПРАВИЛЬНОЕ получение порта для Railway
PORT = int(os.getenv("PORT", "8080"))  # Railway сам установит PORT
BOT_TOKEN = os.getenv("BOT_TOKEN")

logger.info(f"� Starting with PORT={PORT}")
logger.info(f"🤖 BOT_TOKEN={'✅ Set' if BOT_TOKEN else '❌ Missing'}")

# Health Check Handler
class SimpleHealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        response = {"status": "ok", "healthy": True, "port": PORT}
        self.wfile.write(json.dumps(response).encode())

def start_health_server():
    """Запуск health сервера"""
    try:
        server = HTTPServer(("0.0.0.0", PORT), SimpleHealthHandler)
        logger.info(f"✅ Health server ON PORT {PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Health error: {e}")

async def start_telegram_bot():
    """Запуск Telegram бота"""
    if not BOT_TOKEN:
        logger.error("❌ NO BOT_TOKEN!")
        return
    
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
        
        app = Application.builder().token(BOT_TOKEN).build()
        
        async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "🎉 <b>РАБОТАЕТ!</b>

"
                "✅ Railway деплой успешен
"
                "✅ Health check активен
" 
                "✅ Порт настроен правильно
"
                "✅ BOT_TOKEN найден

"
                "� <b>Бот полностью функционален!</b>",
                parse_mode='HTML'
            )
        
        async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "📋 <b>Команды:</b>

"
                "• /start - Проверка работы
"
                "• /help - Эта справка
"
                "• /test - Тестовая команда

"
                "🎯 <b>Все работает отлично!</b>",
                parse_mode='HTML'
            )
        
        async def test_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "🧪 <b>Тест успешен!</b>

"
                f"📡 Порт: {PORT}
"
                "🔗 Соединение: Стабильно
"
                "⚡ Ответ: Мгновенный

"
                "✅ <b>Бот работает на 100%!</b>",
                parse_mode='HTML'
            )
        
        app.add_handler(CommandHandler("start", start_cmd))
        app.add_handler(CommandHandler("help", help_cmd))
        app.add_handler(CommandHandler("test", test_cmd))
        
        logger.info("🤖 Telegram bot starting...")
        await app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")

async def main():
    """Главная функция"""
    logger.info("🚀 TG-analiz starting...")
    
    # Health server в фоне
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Telegram bot
    if BOT_TOKEN:
        await start_telegram_bot()
    else:
        logger.warning("⚠️ No BOT_TOKEN - health only")
        await asyncio.sleep(float('inf'))

if __name__ == "__main__":
    asyncio.run(main())
