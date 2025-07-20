#!/usr/bin/env python3
"""
Telegram Analytics Bot с простым HTTP сервером для Railway
"""
import os
import http.server
import socketserver
import logging
import threading
import asyncio
import time
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        logger.info(f"HTTP запрос: {self.path}")
        
        if self.path in ['/health', '/']:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            logger.info("Health check успешно")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        logger.info(f"HTTP: {format % args}")

def start_health_server():
    """Запуск простого HTTP сервера для health checks"""
    PORT = int(os.environ.get('PORT', 8000))
    logger.info(f"Запуск HTTP сервера на порту {PORT}")
    
    def run_server():
        with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
            logger.info(f"HTTP сервер готов на 0.0.0.0:{PORT}")
            httpd.serve_forever()
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread

async def start_telegram_bot():
    """Запуск Telegram бота (когда будут готовы зависимости)"""
    try:
        # Импорты только когда нужно
        from telegram.ext import Application, CommandHandler
        from config import Config
        from database import Database
        from analytics import AnalyticsCollector
        from reports import ReportGenerator
        
        logger.info("Инициализация Telegram бота...")
        
        config = Config()
        db = Database(config.database_url)
        
        # Инициализация БД
        await db.init_db()
        logger.info("База данных готова")
        
        # Создание бота
        app = Application.builder().token(config.bot_token).build()
        
        # Простые команды для начала
        async def start_command(update, context):
            await update.message.reply_text("🚀 Telegram Analytics Bot запущен!")
        
        app.add_handler(CommandHandler("start", start_command))
        
        # Запуск бота
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        logger.info("Telegram бот запущен успешно!")
        
        # Поддержание работы
        while True:
            await asyncio.sleep(60)
            
    except ImportError as e:
        logger.warning(f"Telegram бот недоступен (нет зависимостей): {e}")
        logger.info("Работаю только как HTTP сервер")
        # Просто ждем
        while True:
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        # Продолжаем работать как HTTP сервер
        while True:
            await asyncio.sleep(60)

async def main():
    """Главная функция"""
    logger.info("=== Запуск Telegram Analytics Bot ===")
    
    # 1. Сначала HTTP сервер (критично для Railway)
    start_health_server()
    logger.info("✅ HTTP сервер запущен")
    
    # Небольшая пауза для стабильности
    await asyncio.sleep(2)
    
    # 2. Затем Telegram бот (если возможно)
    await start_telegram_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        # Важно: не падаем, чтобы HTTP сервер продолжал работать
        logger.info("Поддерживаю HTTP сервер...")
