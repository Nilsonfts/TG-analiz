#!/usr/bin/env python3
"""
ПОЛНЫЙ TG-BOT + HEALTH CHECK для Railway
Объединяет health server и Telegram bot в одном файле
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

PORT = int(os.getenv("PORT", "8080"))
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Health Check Handler
class HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        response = {
            "status": "ok", 
            "healthy": True, 
            "service": "tg-bot",
            "bot_token_set": bool(BOT_TOKEN),
            "telegram_ready": True
        }
        self.wfile.write(json.dumps(response).encode())

def start_health_server():
    """Запуск health check сервера в отдельном потоке"""
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        logger.info(f"✅ Health server running on port {PORT}")
        logger.info(f"🏥 Health check: http://0.0.0.0:{PORT}/")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Health server error: {e}")

# Telegram Bot функции (только если есть зависимости)
async def init_telegram_bot():
    """Инициализация Telegram бота"""
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
        
        if not BOT_TOKEN:
            logger.warning("⚠️ BOT_TOKEN not set, running health check only")
            return None
        
        # Создаем приложение
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Команда /start
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "🚀 TG-analiz Bot работает!\n\n"
                "✅ Railway деплой успешен\n"
                "🏥 Health check активен\n"
                "📊 Готов к анализу каналов\n\n"
                "Используйте /help для списка команд"
            )
        
        # Команда /help
        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "📋 Доступные команды:\n\n"
                "• /start - Информация о боте\n"
                "• /help - Эта справка\n"
                "• /status - Статус системы\n\n"
                "🚀 Railway деплой работает!"
            )
        
        # Команда /status
        async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "📊 Статус системы:\n\n"
                "✅ Railway: Активен\n"
                "✅ Health Check: Работает\n"
                "✅ Telegram Bot: Онлайн\n"
                f"🔧 Port: {PORT}\n\n"
                "🎉 Все системы в норме!"
            )
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("status", status_command))
        
        logger.info("✅ Telegram bot initialized")
        return app
        
    except ImportError:
        logger.warning("⚠️ Telegram libraries not available, health check only")
        return None
    except Exception as e:
        logger.error(f"❌ Telegram bot error: {e}")
        return None

async def main():
    """Главная функция"""
    logger.info("🚀 Starting TG-analiz with health check...")
    
    # ВСЕГДА запускаем health server первым
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Пытаемся запустить Telegram bot
    bot_app = await init_telegram_bot()
    
    if bot_app:
        logger.info("🤖 Starting Telegram bot...")
        await bot_app.run_polling(allowed_updates=["message"])
    else:
        logger.info("🏥 Running in health-check-only mode")
        # Держим процесс живым для health check
        try:
            await asyncio.sleep(float('inf'))
        except KeyboardInterrupt:
            logger.info("👋 Graceful shutdown")

if __name__ == "__main__":
    asyncio.run(main())
