#!/usr/bin/env python3
"""
Telegram Analytics Bot - Шаг 2: Базовые команды + HTTP сервер + База данных
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
    """Запуск Telegram бота с базой данных"""
    try:
        from telegram.ext import Application, CommandHandler
        from telegram import Update
        from telegram.ext import ContextTypes
        from config import Config
        from database import Database
        
        logger.info("Инициализация Telegram бота...")
        
        # Загружаем конфигурацию
        config = Config()
        if not config.bot_token:
            logger.error("BOT_TOKEN не найден в переменных окружения!")
            logger.info("Работаю только как HTTP сервер")
            while True:
                await asyncio.sleep(60)
            return
        
        # Инициализация базы данных
        db = None
        try:
            logger.info("Подключение к базе данных...")
            db = Database(config.database_url)
            await db.init_db()
            logger.info("✅ База данных подключена и инициализирована")
        except Exception as e:
            logger.warning(f"⚠️  База данных недоступна: {e}")
            logger.info("Продолжаю без базы данных")
        
        # Создание приложения бота
        app = Application.builder().token(config.bot_token).build()
        
        # Базовые команды
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            username = update.effective_user.username or "пользователь"
            
            # Сохраняем пользователя в БД если доступна
            if db:
                try:
                    await db.save_user(user_id, username)
                    logger.info(f"Пользователь {username} ({user_id}) сохранен в БД")
                except Exception as e:
                    logger.warning(f"Не удалось сохранить пользователя: {e}")
            
            welcome_text = f"""
🚀 **Добро пожаловать в Telegram Analytics Bot!**

Привет, {username}! 

📊 Доступные команды:
/help - показать эту помощь
/status - статус бота
/ping - проверка связи
/users - количество пользователей (если БД работает)

🔧 Статус: **С базой данных** (Шаг 2/4)
✅ HTTP сервер работает
✅ Telegram бот подключен
{'✅ База данных подключена' if db else '⚠️  База данных недоступна'}
⏳ Аналитика - следующий шаг
⏳ Планировщик - в планах
            """
            
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
            logger.info(f"Команда /start от пользователя {user_id} ({username})")

        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await start_command(update, context)

        async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Проверяем статус БД
            db_status = "✅ Подключена" if db else "❌ Недоступна"
            users_count = 0
            
            if db:
                try:
                    users_count = await db.get_users_count()
                    db_status = f"✅ Подключена ({users_count} пользователей)"
                except:
                    db_status = "⚠️  Подключена, но есть ошибки"
            
            status_text = f"""
🤖 **Статус Telegram Analytics Bot**

✅ HTTP сервер: Работает
✅ Telegram API: Подключен  
✅ Railway деплой: Активен
{db_status.split()[0]} База данных: {db_status}
⏳ Аналитика: Не активна
⏳ Планировщик: Не запущен

🏗️ **Текущая стадия**: База данных (2/4)
📊 **Пользователей в системе**: {users_count}
            """
            await update.message.reply_text(status_text, parse_mode='Markdown')

        async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text("🏓 Pong! Бот работает отлично!")

        async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            try:
                count = await db.get_users_count()
                users_list = await db.get_recent_users(limit=10)
                
                text = f"👥 **Пользователи в системе**: {count}\n\n"
                text += "🆕 **Последние 10 пользователей:**\n"
                
                for user in users_list:
                    text += f"• {user['username'] or 'Без имени'} (ID: {user['user_id']})\n"
                
                await update.message.reply_text(text, parse_mode='Markdown')
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка получения данных: {e}")

        # Регистрация обработчиков
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("ping", ping_command))
        app.add_handler(CommandHandler("users", users_command))
        
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
    logger.info("=== 🚀 Запуск Telegram Analytics Bot (Шаг 2/4) ===")
    
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
