#!/usr/bin/env python3
"""
Telegram Analytics Bot - Шаг 4: ФИНАЛ - Полный функционал с планировщиком
"""
import os
import http.server
import socketserver
import logging
import threading
import asyncio
import time
import schedule

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

async def send_scheduled_reports(app, db, reports, report_type):
    """Отправка автоматических отчетов подписчикам"""
    try:
        logger.info(f"Начинаю отправку {report_type} отчетов...")
        
        # Получаем подписчиков
        subscribers = await db.get_subscribers(report_type)
        if not subscribers:
            logger.info(f"Нет подписчиков для {report_type} отчетов")
            return
        
        # Генерируем отчет
        if report_type == 'daily':
            report = await reports.generate_daily_report()
        elif report_type == 'weekly':
            report = await reports.generate_weekly_report()
        else:
            logger.error(f"Неизвестный тип отчета: {report_type}")
            return
        
        # Отправляем всем подписчикам
        sent_count = 0
        for user_id in subscribers:
            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text=f"📊 <b>Автоматический {report_type} отчет</b>\n\n{report}",
                    parse_mode='HTML'
                )
                sent_count += 1
                logger.info(f"Отчет отправлен пользователю {user_id}")
                
                # Небольшая пауза между отправками
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Ошибка отправки отчета пользователю {user_id}: {e}")
        
        logger.info(f"✅ {report_type} отчеты отправлены {sent_count} подписчикам")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке {report_type} отчетов: {e}")

async def start_telegram_bot():
    """Запуск Telegram бота с базой данных"""
    try:
        from telegram.ext import Application, CommandHandler
        from telegram import Update
        from telegram.ext import ContextTypes
        from config import Config
        from database import Database
        from reports import ReportGenerator
        
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
        reports = None
        scheduler_running = False
        try:
            logger.info("Подключение к базе данных...")
            logger.info(f"DATABASE_URL доступен: {bool(config.database_url)}")
            
            db = Database(config.database_url)
            await db.init_db()
            reports = ReportGenerator(db)
            logger.info("✅ База данных подключена и инициализирована")
        except Exception as e:
            logger.warning(f"⚠️  База данных недоступна: {e}")
            logger.warning(f"Тип ошибки: {type(e).__name__}")
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
/daily - дневной отчет
/weekly - недельный отчет
/demo - демо отчет с тестовыми данными
/subscribe daily|weekly - подписаться на автоматические отчеты
/unsubscribe daily|weekly - отписаться от отчетов

🔧 Статус: **ПОЛНЫЙ ФУНКЦИОНАЛ** (Шаг 4/4)
✅ HTTP сервер работает
✅ Telegram бот подключен
{'✅ База данных подключена' if db else '⚠️  База данных недоступна'}
{'✅ Отчеты доступны' if reports else '⚠️  Отчеты недоступны'}
{'✅ Планировщик запущен' if scheduler_running else '⏳ Планировщик настраивается'}
            """
            
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
            logger.info(f"Команда /start от пользователя {user_id} ({username})")

        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await start_command(update, context)

        async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Проверяем статус БД
            db_status = "✅ Подключена" if db else "❌ Недоступна"
            reports_status = "✅ Доступны" if reports else "❌ Недоступны"
            scheduler_status = "✅ Запущен" if scheduler_running else "❌ Не запущен"
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
{reports_status.split()[0]} Отчеты: {reports_status}
{scheduler_status.split()[0]} Планировщик: {scheduler_status}

🏗️ **Текущая стадия**: ПОЛНЫЙ ФУНКЦИОНАЛ (4/4) ✅
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

        async def daily_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not reports:
                await update.message.reply_text("❌ Система отчетов недоступна")
                return
            
            try:
                await update.message.reply_text("📊 Генерирую дневной отчет...")
                report = await reports.generate_daily_report()
                await update.message.reply_text(report, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Ошибка генерации дневного отчета: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации отчета: {e}")

        async def weekly_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not reports:
                await update.message.reply_text("❌ Система отчетов недоступна")
                return
            
            try:
                await update.message.reply_text("📈 Генерирую недельный отчет...")
                report = await reports.generate_weekly_report()
                await update.message.reply_text(report, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Ошибка генерации недельного отчета: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации отчета: {e}")

        async def demo_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Демо отчет с тестовыми данными"""
            demo_report = """
📊 <b>ДЕМО ОТЧЕТ - Дневная аналитика</b>

📅 <b>Дата:</b> 20 июля 2025
🕐 <b>Период:</b> Последние 24 часа

📈 <b>ОБЩАЯ СТАТИСТИКА:</b>
💬 Сообщений: 1,247 (+15%)
👥 Активных пользователей: 89 (+8%)
📋 Новых участников: 5
🔗 Пересланных сообщений: 23

🏆 <b>ТОП АКТИВНОСТИ:</b>
🥇 @user1 - 47 сообщений
🥈 @user2 - 32 сообщения  
🥉 @user3 - 28 сообщений

⏰ <b>АКТИВНОСТЬ ПО ЧАСАМ:</b>
🌅 06:00-12:00: 287 сообщений
🌞 12:00-18:00: 456 сообщений (пик)
🌙 18:00-00:00: 398 сообщений
🌃 00:00-06:00: 106 сообщений

📊 <b>ТИПЫ КОНТЕНТА:</b>
💬 Текст: 89% (1,110 сообщений)
🖼 Медиа: 8% (97 сообщений)
📎 Файлы: 3% (40 сообщений)

✨ <i>Это демо версия. Реальные данные будут доступны после настройки мониторинга групп.</i>
            """
            await update.message.reply_text(demo_report, parse_mode='HTML')

        async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            if not context.args:
                await update.message.reply_text("""
📋 **Доступные подписки:**

/subscribe daily - дневные отчеты (каждый день в 09:00)
/subscribe weekly - недельные отчеты (по понедельникам в 09:00)

Пример: `/subscribe daily`
                """, parse_mode='Markdown')
                return
            
            report_type = context.args[0].lower()
            if report_type not in ['daily', 'weekly']:
                await update.message.reply_text("❌ Доступные типы: daily, weekly")
                return
            
            user_id = update.effective_user.id
            try:
                await db.subscribe_user(user_id, report_type)
                await update.message.reply_text(f"✅ Вы подписались на {report_type} отчеты!")
                logger.info(f"Пользователь {user_id} подписался на {report_type}")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка подписки: {e}")

        async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            if not context.args:
                await update.message.reply_text("""
📋 **Отписка от уведомлений:**

/unsubscribe daily - отписаться от дневных отчетов  
/unsubscribe weekly - отписаться от недельных отчетов

Пример: `/unsubscribe daily`
                """, parse_mode='Markdown')
                return
            
            report_type = context.args[0].lower()
            if report_type not in ['daily', 'weekly']:
                await update.message.reply_text("❌ Доступные типы: daily, weekly")
                return
            
            user_id = update.effective_user.id
            try:
                await db.unsubscribe_user(user_id, report_type)
                await update.message.reply_text(f"✅ Вы отписались от {report_type} отчетов!")
                logger.info(f"Пользователь {user_id} отписался от {report_type}")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка отписки: {e}")

        # Регистрация обработчиков
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("ping", ping_command))
        app.add_handler(CommandHandler("users", users_command))
        app.add_handler(CommandHandler("daily", daily_report_command))
        app.add_handler(CommandHandler("weekly", weekly_report_command))
        app.add_handler(CommandHandler("demo", demo_report_command))
        app.add_handler(CommandHandler("subscribe", subscribe_command))
        app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
        
        # Запуск бота
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        logger.info("✅ Telegram бот запущен успешно!")
        
        # Настройка планировщика
        if db and reports:
            try:
                # Функции для автоматических отчетов
                def send_daily_reports():
                    asyncio.create_task(send_scheduled_reports(app, db, reports, 'daily'))
                
                def send_weekly_reports():
                    asyncio.create_task(send_scheduled_reports(app, db, reports, 'weekly'))
                
                # Настройка расписания
                schedule.every().day.at("09:00").do(send_daily_reports)
                schedule.every().monday.at("09:00").do(send_weekly_reports)
                
                # Запуск планировщика в отдельном потоке
                def run_scheduler():
                    nonlocal scheduler_running
                    scheduler_running = True
                    logger.info("✅ Планировщик запущен - отчеты будут отправляться автоматически")
                    logger.info("📅 Дневные отчеты: каждый день в 09:00")
                    logger.info("📅 Недельные отчеты: каждый понедельник в 09:00")
                    
                    while True:
                        schedule.run_pending()
                        time.sleep(60)
                
                scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
                scheduler_thread.start()
                
            except Exception as e:
                logger.error(f"Ошибка настройки планировщика: {e}")
        else:
            logger.warning("⚠️  Планировщик не запущен (нет БД или системы отчетов)")
        
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
    logger.info("=== 🚀 Запуск Telegram Analytics Bot (Шаг 4/4) ===")
    logger.info("🎯 ФИНАЛЬНАЯ ВЕРСИЯ - Полный функционал готов!")
    
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
