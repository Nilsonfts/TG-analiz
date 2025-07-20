#!/usr/bin/env python3
"""
Telegram Analytics Bot - Шаг 1: Базовые команды + HTTP сервер
"""
import os
import http.server
import socketserver
import logging
import threading
import asyncio
import time

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
    """Запуск HTTP сервера для Railway health checks"""
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
    """Запуск базового Telegram бота"""
    try:
        from telegram.ext import Application, CommandHandler
        from telegram import Update
        from telegram.ext import ContextTypes
        
        logger.info("Инициализация Telegram бота...")
        
        # Получаем токен из переменной окружения
        BOT_TOKEN = os.getenv('BOT_TOKEN')
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN не найден в переменных окружения!")
            return
        
        # Создание приложения бота
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Базовые команды
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            username = update.effective_user.username or "пользователь"
            
            welcome_text = f"""
🚀 **Добро пожаловать в Telegram Analytics Bot!**

Привет, {username}! 

📊 Доступные команды:
/help - показать эту помощь
/status - статус бота
/ping - проверка связи

🔧 Статус: **Базовая версия** (Шаг 1/4)
✅ HTTP сервер работает
✅ Telegram бот подключен
⏳ База данных - следующий шаг
⏳ Аналитика - в разработке
⏳ Планировщик - в планах
            """
            
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
            logger.info(f"Команда /start от пользователя {user_id} ({username})")

        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await start_command(update, context)

        async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            status_text = """
🤖 **Статус Telegram Analytics Bot**

✅ HTTP сервер: Работает
✅ Telegram API: Подключен  
✅ Railway деплой: Активен
⏳ База данных: Не подключена
⏳ Аналитика: Не активна
⏳ Планировщик: Не запущен

🏗️ **Текущая стадия**: Базовые команды (1/4)
            """
            await update.message.reply_text(status_text, parse_mode='Markdown')

        async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text("🏓 Pong! Бот работает отлично!")

        # Регистрация обработчиков
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("ping", ping_command))
        
        # Запуск бота
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        logger.info("✅ Telegram бот запущен успешно!")
        
        # Поддержание работы
        while True:
            await asyncio.sleep(60)
            
    except ImportError as e:
        logger.warning(f"Telegram бот недоступен (нет зависимостей): {e}")
        logger.info("Работаю только как HTTP сервер")
        while True:
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        logger.info("Продолжаю работать как HTTP сервер")
        while True:
            await asyncio.sleep(60)

async def main():
    """Главная функция"""
    logger.info("=== 🚀 Запуск Telegram Analytics Bot (Шаг 1/4) ===")
    
    # 1. HTTP сервер ПЕРВЫМ (критично для Railway)
    start_health_server()
    logger.info("✅ HTTP сервер запущен")
    
    # Пауза для стабильности
    await asyncio.sleep(2)
    
    # 2. Telegram бот
    await start_telegram_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        logger.info("Поддерживаю HTTP сервер...")
import os
import http.server
import socketserver
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthOnlyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        logger.info(f"Получен запрос: {self.path}")
        
        # Отвечаем OK на любой запрос
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')
        
        logger.info(f"Отправлен ответ 200 OK")
    
    def log_message(self, format, *args):
        logger.info(format % args)

if __name__ == "__main__":
    PORT = int(os.environ.get('PORT', 8000))
    
    logger.info(f"Запуск сервера на порту {PORT}")
    logger.info(f"Переменная PORT из окружения: {os.environ.get('PORT', 'НЕ УСТАНОВЛЕНА')}")
    
    with socketserver.TCPServer(("", PORT), HealthOnlyHandler) as httpd:
        logger.info(f"Сервер слушает на 0.0.0.0:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Сервер остановлен")
