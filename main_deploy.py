#!/usr/bin/env python3
"""
Упрощенная версия main.py с улучшенным healthcheck для деплоя
"""
import os
import http.server
import socketserver
import logging
import threading
import asyncio
import signal
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные
app_running = True
bot_status = "starting"

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """Отключаем логи HTTP запросов"""
        pass
        
    def do_GET(self):
        global app_running, bot_status
        
        if self.path == "/health":
            # Health check endpoint
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            health_data = {
                "status": "healthy" if app_running and bot_status == "running" else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "app_running": app_running,
                "bot_status": bot_status,
                "service": "telegram-channel-analytics"
            }
            
            import json
            self.wfile.write(json.dumps(health_data).encode())
            
        elif self.path == "/":
            # Главная страница
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            status_emoji = "🟢" if app_running and bot_status == "running" else "🟡" if bot_status == "starting" else "🔴"
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Telegram Channel Analytics Bot</title>
                <meta charset="utf-8">
                <meta http-equiv="refresh" content="30">
            </head>
            <body>
                <h1>📊 Telegram Channel Analytics Bot</h1>
                <p>{status_emoji} Статус: {bot_status}</p>
                <p>🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>🚀 Готов к анализу каналов</p>
                <hr>
                <h3>📋 Доступные команды:</h3>
                <ul>
                    <li>/summary - 📊 Сводная статистика</li>
                    <li>/growth - 📈 Рост подписчиков</li>
                    <li>/engagement - ⚡ Вовлеченность</li>
                    <li>/traffic - 🎯 Источники трафика</li>
                    <li>/charts - 📊 Графики</li>
                </ul>
                <p><a href="/health">Health Check JSON</a></p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not Found"}')

def start_http_server():
    """Запуск HTTP сервера"""
    global app_running
    
    port = int(os.environ.get("PORT", 8000))
    
    try:
        with socketserver.TCPServer(("", port), HealthHandler) as httpd:
            logger.info(f"🌐 HTTP сервер запущен на порту {port}")
            while app_running:
                httpd.handle_request()
    except Exception as e:
        logger.error(f"❌ Ошибка HTTP сервера: {e}")

async def start_telegram_bot():
    """Запуск Telegram бота"""
    global app_running, bot_status
    
    try:
        # Попытка импорта и инициализации
        bot_status = "initializing"
        
        from config import BOT_TOKEN
        if not BOT_TOKEN:
            logger.warning("⚠️ BOT_TOKEN не найден - работаю только как HTTP сервер")
            bot_status = "http_only"
            while app_running:
                await asyncio.sleep(60)
            return
            
        # Импорт Telegram бота
        from telegram.ext import Application
        
        logger.info("🤖 Инициализация Telegram бота...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Простая команда start
        async def start_command(update, context):
            await update.message.reply_text(
                "🚀 Привет! Я бот аналитики каналов.\n"
                "📊 Система работает и готова к анализу!"
            )
        
        from telegram.ext import CommandHandler
        application.add_handler(CommandHandler("start", start_command))
        
        bot_status = "running"
        logger.info("✅ Telegram бот запущен")
        
        # Запуск бота
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Ожидание завершения
        while app_running:
            await asyncio.sleep(1)
            
    except ImportError as e:
        logger.warning(f"⚠️ Модули не найдены: {e}")
        bot_status = "http_only"
        while app_running:
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"❌ Ошибка бота: {e}")
        bot_status = "error"
        while app_running:
            await asyncio.sleep(60)

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global app_running
    logger.info(f"📨 Получен сигнал {signum}")
    app_running = False

async def main():
    """Главная функция"""
    global app_running, bot_status
    
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("🚀 Запуск Telegram Channel Analytics Bot")
    logger.info("📊 Версия: Channel Analytics v2.0")
    
    # Запуск HTTP сервера в отдельном потоке
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    # Ожидание инициализации HTTP сервера
    await asyncio.sleep(2)
    bot_status = "ready"
    
    # Запуск Telegram бота
    try:
        await start_telegram_bot()
    except KeyboardInterrupt:
        logger.info("⌨️ Получен сигнал завершения")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        bot_status = "error"
    finally:
        app_running = False
        bot_status = "stopped"
        logger.info("👋 Telegram Analytics Bot завершил работу")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⌨️ Программа прервана пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при запуске: {e}")
        sys.exit(1)
