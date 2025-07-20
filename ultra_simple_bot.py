#!/usr/bin/env python3
"""
УЛЬТРА-ПРОСТОЙ TG-analiz Bot для Railway
МИНИМУМ КОДА - МАКСИМУМ НАДЕЖНОСТИ
"""
import asyncio
import json
import logging
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Логи
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Railway конфигурация
PORT = int(os.getenv("PORT", "8080"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Подробные логи
logger.info("=" * 50)
logger.info("🚀 УЛЬТРА-ПРОСТОЙ TG-ANALIZ СТАРТУЕТ")
logger.info("=" * 50)
logger.info(f"🌐 PORT: {PORT}")
logger.info(f"🤖 BOT_TOKEN: {'✅ НАЙДЕН' if BOT_TOKEN else '❌ НЕ НАЙДЕН'}")
logger.info(f"🔗 Python: {sys.version}")
logger.info("=" * 50)

class UltraHealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        logger.info(f"🏥 Health check запрос от {self.client_address}")
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        health_data = {
            "status": "ok",
            "healthy": True,
            "port": PORT,
            "bot_token_set": bool(BOT_TOKEN),
            "timestamp": asyncio.get_event_loop().time() if hasattr(asyncio, 'get_event_loop') else 0
        }
        
        response = json.dumps(health_data, indent=2)
        self.wfile.write(response.encode('utf-8'))
        logger.info("✅ Health check ответ отправлен")

def start_health_server():
    """Запуск health сервера"""
    try:
        logger.info(f"🏥 Запуск health сервера на порту {PORT}")
        server = HTTPServer(("0.0.0.0", PORT), UltraHealthHandler)
        logger.info(f"✅ Health сервер АКТИВЕН на 0.0.0.0:{PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ ОШИБКА health сервера: {e}")
        sys.exit(1)

async def ultra_simple_bot():
    """Ультра-простой Telegram бот"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN НЕ НАЙДЕН!")
        logger.error("Проверьте Railway Variables!")
        return
    
    try:
        logger.info("📦 Импорт telegram библиотек...")
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes
        logger.info("✅ Telegram библиотеки импортированы")
        
        # Создание приложения
        logger.info("🔧 Создание Telegram приложения...")
        app = Application.builder().token(BOT_TOKEN).build()
        logger.info("✅ Telegram приложение создано")
        
        # Команда /start
        async def ultra_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info(f"📨 /start от пользователя {update.effective_user.id}")
            
            message = (
                "🎉 <b>УЛЬТРА-ПРОСТОЙ БОТА РАБОТАЕТ!</b>\n\n"
                f"✅ Railway деплой: ОК\n"
                f"✅ Health check: ОК\n"
                f"✅ Порт {PORT}: ОК\n"
                f"✅ BOT_TOKEN: ОК\n"
                f"✅ Telegram API: ОК\n\n"
                f"👤 Ваш ID: <code>{update.effective_user.id}</code>\n"
                f"💬 Чат ID: <code>{update.effective_chat.id}</code>\n\n"
                "🚀 <b>ВСЕ СИСТЕМЫ В НОРМЕ!</b>"
            )
            
            await update.message.reply_text(message, parse_mode='HTML')
            logger.info("✅ Ответ /start отправлен")
        
        # Команда /ping
        async def ultra_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info(f"📨 /ping от пользователя {update.effective_user.id}")
            await update.message.reply_text("🏓 <b>PONG!</b> Бот живой!", parse_mode='HTML')
            logger.info("✅ Ответ /ping отправлен")
        
        # Команда /info
        async def ultra_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.info(f"📨 /info от пользователя {update.effective_user.id}")
            
            info_text = (
                "ℹ️ <b>Информация о боте:</b>\n\n"
                f"🌐 Порт: {PORT}\n"
                f"🤖 Версия: Ультра-простая\n"
                f"☁️ Платформа: Railway\n"
                f"🐍 Python: {sys.version.split()[0]}\n\n"
                "📋 <b>Команды:</b>\n"
                "• /start - Проверка работы\n"
                "• /ping - Быстрый тест\n"
                "• /info - Эта информация\n\n"
                "✅ <b>Все работает отлично!</b>"
            )
            
            await update.message.reply_text(info_text, parse_mode='HTML')
            logger.info("✅ Ответ /info отправлен")
        
        # Регистрация команд
        logger.info("📋 Регистрация команд...")
        app.add_handler(CommandHandler("start", ultra_start))
        app.add_handler(CommandHandler("ping", ultra_ping))
        app.add_handler(CommandHandler("info", ultra_info))
        logger.info("✅ Команды зарегистрированы: /start, /ping, /info")
        
        # Запуск бота
        logger.info("🤖 ЗАПУСК TELEGRAM БОТА...")
        logger.info("=" * 50)
        await app.run_polling(drop_pending_updates=True)
        
    except ImportError as e:
        logger.error(f"❌ ОШИБКА импорта: {e}")
        logger.error("Проверьте requirements.txt!")
    except Exception as e:
        logger.error(f"❌ ОШИБКА бота: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

async def main():
    """Главная функция"""
    logger.info("🚀 СТАРТ ГЛАВНОЙ ФУНКЦИИ")
    
    # Health сервер в отдельном потоке
    logger.info("🏥 Запуск health сервера в фоне...")
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Небольшая пауза
    await asyncio.sleep(1)
    
    # Telegram бот
    logger.info("🤖 Запуск Telegram бота...")
    await ultra_simple_bot()

if __name__ == "__main__":
    try:
        logger.info("🎬 ЗАПУСК ПРИЛОЖЕНИЯ")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        sys.exit(1)
