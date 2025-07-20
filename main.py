#!/usr/bin/env python3
"""
Telegram Analytics Bot - Полный функционал с графиками и визуализацией
"""
import os
import http.server
import socketserver
import logging
import threading
import asyncio
import time
import schedule
import signal
import sys
from datetime import datetime, timedelta

# Telegram Bot API
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Наши модули
from visualization import ChartGenerator
from alerts import AlertSystem
from data_export import DataExporter

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные для graceful shutdown
app_running = True
telegram_app = None

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
    global telegram_app, app_running
    
    try:
        from config import Config
        from database import Database
        from reports import ReportGenerator
        
        logger.info("Инициализация Telegram бота...")
        
        # Загружаем конфигурацию
        config = Config()
        if not config.bot_token:
            logger.error("BOT_TOKEN не найден в переменных окружения!")
            logger.info("Работаю только как HTTP сервер")
            while app_running:
                await asyncio.sleep(60)
            return

        # Принудительно выводим информацию о DATABASE_URL
        logger.info("=" * 50)
        logger.info("ДИАГНОСТИКА БАЗЫ ДАННЫХ:")
        logger.info(f"DATABASE_URL присутствует: {bool(config.database_url)}")
        if config.database_url:
            logger.info(f"DATABASE_URL (первые 50 символов): {config.database_url[:50]}...")
            logger.info(f"DATABASE_URL (последние 20 символов): ...{config.database_url[-20:]}")
        else:
            logger.error("DATABASE_URL полностью отсутствует!")
        logger.info("=" * 50)
        
        # Инициализация базы данных
        db = None
        reports = None
        scheduler_running = False
        try:
            logger.info("Подключение к базе данных...")
            logger.info(f"DATABASE_URL доступен: {bool(config.database_url)}")
            if config.database_url:
                logger.info(f"DATABASE_URL начинается с: {config.database_url[:20]}...")
            else:
                logger.error("DATABASE_URL не установлен!")
                logger.error("Проверьте переменные окружения в Railway:")
                logger.error("- DATABASE_PUBLIC_URL")
                logger.error("- DATABASE_URL") 
            
            logger.info("Создание объекта Database...")
            db = Database(config.database_url)
            logger.info("Объект Database создан, начинаем инициализацию...")
            
            await db.init_db()
            logger.info("✅ База данных подключена и инициализирована")
            
            # Создаем генератор отчетов если БД работает
            try:
                reports = ReportGenerator(db)
                logger.info("✅ Система отчетов инициализирована")
            except Exception as reports_error:
                logger.warning(f"⚠️  Ошибка инициализации отчетов: {reports_error}")
                
        except Exception as e:
            logger.error("❌" * 20)
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА БАЗЫ ДАННЫХ: {e}")
            logger.error(f"❌ Тип ошибки: {type(e).__name__}")
            logger.error(f"❌ Подробности ошибки: {str(e)}")
            if hasattr(e, '__traceback__'):
                import traceback
                logger.error(f"❌ Трассировка:\n{traceback.format_exc()}")
            logger.error("❌" * 20)
            logger.info("Продолжаю без базы данных")
        
        # Создание приложения бота
        app = Application.builder().token(config.bot_token).build()
        telegram_app = app  # Сохраняем глобальную ссылку
        
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
🚀 **Telegram Analytics Bot с графиками!**

Привет, {username}! 

📊 **Новые возможности:**
• /charts - 📈 графики активности 
• /trend - 📊 динамика за месяц
• /dashboard - 🎯 сводная панель

**📋 Основные команды:**
• /help - справка по всем командам
• /status - статус системы
• /daily - дневной отчёт
• /weekly - недельный отчёт

**🔔 Подписки:**
• /subscribe daily - автоматические дневные отчёты
• /subscribe weekly - автоматические недельные отчёты

🎨 **Статус: ГРАФИКИ И ВИЗУАЛИЗАЦИЯ**
✅ HTTP сервер работает
✅ Telegram бот подключен
{'✅ База данных подключена' if db else '⚠️  База данных недоступна'}
{'✅ Отчеты и графики доступны' if reports else '⚠️  Отчеты недоступны'}
{'✅ Планировщик запущен' if scheduler_running else '⏳ Планировщик настраивается'}

Используйте /help для полного списка команд!
            """
            
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
            logger.info(f"Команда /start от пользователя {user_id} ({username})")

        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            help_text = """
🤖 **Telegram Analytics Bot - Справка**

**📊 Основные команды:**
• /status - статус системы
• /users - статистика пользователей  
• /daily - дневной отчёт
• /weekly - недельный отчёт
• /summary - сводный аналитический отчёт
• /demo - демо отчёт

**📈 Графики и аналитика:**
• /charts - графики активности по часам и топ пользователи
• /trend - график динамики за 30 дней
• /dashboard - сводная аналитическая панель
• /export [messages|users|analytics|full] - экспорт данных в CSV

**🔔 Подписки:**
• /subscribe [daily|weekly] - подписаться на автоотчёты
• /unsubscribe [daily|weekly] - отписаться

**👑 Админские команды:**
• /groupinfo - информация о группе
• /addgroup [ID] - добавить группу в мониторинг
• /alerts - проверить алерты системы мониторинга
• /debug - диагностика системы
• /testdb - тест базы данных

**ℹ️ Автоматические процессы:**
📅 Дневные отчёты: каждый день в 09:00
📅 Недельные отчёты: каждый понедельник в 09:00
🚨 Проверка алертов: каждые 30 минут

Добавьте бота в группу как администратора для начала мониторинга!
            """
            await update.message.reply_text(help_text, parse_mode='Markdown')

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

        async def groupinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Получение информации о текущей группе"""
            chat = update.effective_chat
            user = update.effective_user
            
            # Проверяем, что команда вызвана в группе
            if chat.type not in ['group', 'supergroup']:
                await update.message.reply_text("❌ Эта команда работает только в группах!")
                return
            
            # Проверяем, что пользователь администратор
            try:
                chat_member = await context.bot.get_chat_member(chat.id, user.id)
                if chat_member.status not in ['administrator', 'creator']:
                    await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                    return
            except Exception as e:
                logger.warning(f"Не удалось проверить права пользователя: {e}")
            
            group_info = f"""
🏛️ **Информация о группе**

📋 **Название:** {chat.title or 'Без названия'}
🆔 **ID группы:** `{chat.id}`
👤 **Username:** @{chat.username or 'Не установлен'}
👥 **Тип:** {chat.type}

📊 **Для мониторинга этой группы:**
1. Скопируйте ID группы: `{chat.id}`
2. Добавьте группу в систему командой `/addgroup {chat.id}`

⚙️ **Текущий статус мониторинга:**
{'✅ Группа уже отслеживается' if db else '⚠️  База данных недоступна - сначала исправьте подключение к БД'}
            """
            
            await update.message.reply_text(group_info, parse_mode='Markdown')
            logger.info(f"Информация о группе {chat.id} запрошена пользователем {user.id}")

        async def addgroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Добавление группы в систему мониторинга"""
            if not db or not db.pool:
                await update.message.reply_text("❌ База данных недоступна. Проверьте подключение к PostgreSQL.")
                logger.error("База данных не инициализирована при попытке добавить группу")
                return
            
            user_id = update.effective_user.id
            
            # Отладочная информация
            logger.info(f"Команда /addgroup от пользователя {user_id}")
            logger.info(f"Администраторы бота: {config.admin_users}")
            
            # Проверяем, что пользователь администратор бота
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы бота могут добавлять группы!")
                logger.warning(f"Пользователь {user_id} не является администратором")
                return
            
            if not context.args:
                await update.message.reply_text("""
📋 **Добавление группы в мониторинг:**

Использование: `/addgroup <ID_группы>`

1. Добавьте бота в группу как администратора
2. В группе выполните команду `/groupinfo` 
3. Скопируйте ID группы
4. Выполните `/addgroup <ID_группы>`

Пример: `/addgroup -1001234567890`
                """, parse_mode='Markdown')
                return
            
            try:
                group_id = int(context.args[0])
                
                # Получаем информацию о группе
                try:
                    chat = await context.bot.get_chat(group_id)
                    members_count = await context.bot.get_chat_member_count(group_id)
                    
                    # Создаем объект группы
                    from database import TelegramGroup
                    group = TelegramGroup(
                        group_id=group_id,
                        username=chat.username,
                        title=chat.title,
                        description=chat.description,
                        members_count=members_count,
                        is_active=True
                    )
                    
                    # Добавляем в базу данных
                    await db.add_group(group)
                    
                    await update.message.reply_text(f"""
✅ **Группа добавлена в систему мониторинга!**

📋 **Название:** {chat.title}
🆔 **ID:** `{group_id}`
👥 **Участников:** {members_count}

🚀 **Что дальше:**
- Бот будет отслеживать активность в группе
- Генерировать ежедневные и еженедельные отчеты
- Пользователи могут подписаться на автоматические отчеты
                    """, parse_mode='Markdown')
                    
                    logger.info(f"Группа {group_id} ({chat.title}) добавлена администратором {user_id}")
                    
                except Exception as e:
                    await update.message.reply_text(f"❌ Ошибка получения информации о группе: {e}")
                    
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID группы. Используйте числовой ID.")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка добавления группы: {e}")

        async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Отладочная информация для диагностики проблем"""
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            debug_info = f"""
🔍 **Отладочная информация**

**Конфигурация:**
• BOT_TOKEN: {'✅ Установлен' if config.bot_token else '❌ Не найден'}
• DATABASE_URL: {'✅ Установлен' if config.database_url else '❌ Не найден'}
• ADMIN_USERS: {config.admin_users}

**База данных:**
• Объект db: {'✅ Создан' if db else '❌ Не создан'}
• Пул подключений: {'✅ Активен' if db and db.pool else '❌ Неактивен'}

**Системы:**
• Отчеты: {'✅ Работают' if reports else '❌ Недоступны'}
• Планировщик: {'✅ Запущен' if scheduler_running else '❌ Остановлен'}

**Переменные окружения (первые символы):**
• DATABASE_URL: {config.database_url[:30] + '...' if config.database_url else 'Не установлен'}
            """
            
            await update.message.reply_text(debug_info, parse_mode='Markdown')

        async def testdb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Тестирование подключения к базе данных"""
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            # Получаем все возможные переменные БД
            import os
            db_vars = {}
            possible_vars = [
                'DATABASE_URL', 'DATABASE_PUBLIC_URL', 'POSTGRES_URL', 'POSTGRES_PUBLIC_URL',
                'DB_URL', 'DB_PUBLIC_URL', 'RAILWAY_DATABASE_URL', 'PGUSER', 'PGHOST', 
                'PGPORT', 'PGDATABASE', 'POSTGRES_PASSWORD', 'RAILWAY_TCP_PROXY_DOMAIN',
                'RAILWAY_TCP_PROXY_PORT', 'RAILWAY_PRIVATE_DOMAIN'
            ]
            
            for var in possible_vars:
                value = os.getenv(var)
                if value:
                    # Маскируем пароль для безопасности
                    if 'postgresql://' in value and ':' in value:
                        masked = value.split('://')[0] + '://***:***@' + value.split('@')[1] if '@' in value else value[:30] + '...'
                    else:
                        masked = value[:30] + '...' if len(value) > 30 else value
                    db_vars[var] = masked
            
            test_info = f"""🔧 Тест базы данных

Найденные переменные:
{chr(10).join([f'• {k}: {v}' for k, v in db_vars.items()]) if db_vars else '• Переменные БД не найдены'}

Текущая конфигурация:
• Используется: {config.database_url[:30] + '...' if config.database_url else 'Не установлен'}
• Содержит localhost: {'Да' if config.database_url and ('localhost' in config.database_url or '127.0.0.1' in config.database_url) else 'Нет'}

Попытка собрать внешний URL:"""

            # Пытаемся собрать внешний URL из компонентов
            pguser = os.getenv('PGUSER')
            pgpass = os.getenv('POSTGRES_PASSWORD') 
            pghost = os.getenv('RAILWAY_TCP_PROXY_DOMAIN')
            pgport = os.getenv('RAILWAY_TCP_PROXY_PORT')
            pgdb = os.getenv('PGDATABASE')
            
            if all([pguser, pgpass, pghost, pgport, pgdb]):
                manual_url = f"postgresql://{pguser}:{pgpass}@{pghost}:{pgport}/{pgdb}"
                test_info += f"""
• MANUAL_URL: {manual_url[:50]}...
• Содержит localhost: {'Да' if 'localhost' in manual_url else 'Нет'}

Рекомендация:
{'Используйте собранный URL выше' if 'localhost' not in manual_url else 'Добавьте DATABASE_PUBLIC_URL с внешним адресом PostgreSQL'}
"""
            else:
                test_info += f"""

Компоненты для сборки URL:
• PGUSER: {'✅' if pguser else '❌'}
• POSTGRES_PASSWORD: {'✅' if pgpass else '❌'}
• RAILWAY_TCP_PROXY_DOMAIN: {'✅' if pghost else '❌'}
• RAILWAY_TCP_PROXY_PORT: {'✅' if pgport else '❌'}  
• PGDATABASE: {'✅' if pgdb else '❌'}

Рекомендация:
Добавьте DATABASE_PUBLIC_URL с внешним адресом PostgreSQL
"""
            
            await update.message.reply_text(test_info)

        # === НОВЫЕ КОМАНДЫ С ГРАФИКАМИ ===
        
        async def charts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Команда для получения графиков активности"""
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            await update.message.reply_text("📊 Генерирую графики активности...")
            
            try:
                # Получаем активные группы
                groups = await db.get_active_groups()
                if not groups:
                    await update.message.reply_text("❌ Нет активных групп для анализа")
                    return
                
                group = groups[0]  # Берём первую группу
                chart_gen = ChartGenerator()
                
                # Получаем данные для графиков
                hourly_data = await db.get_hourly_activity(group.group_id, days=7)
                top_users_data = await db.get_daily_stats(group.group_id, datetime.now())
                
                # Создаём график активности по часам
                if hourly_data:
                    chart_buf = chart_gen.create_activity_chart(
                        hourly_data, 
                        f"Активность в группе '{group.title}' (7 дней)"
                    )
                    
                    if chart_buf:
                        await update.message.reply_photo(
                            photo=chart_buf,
                            caption=f"📊 График активности по часам\n🏷️ Группа: {group.title}\n📅 Период: 7 дней"
                        )
                
                # Создаём график топ пользователей
                if top_users_data and top_users_data['top_users']:
                    chart_buf = chart_gen.create_top_users_chart(
                        top_users_data['top_users'],
                        f"Топ пользователей группы '{group.title}'"
                    )
                    
                    if chart_buf:
                        await update.message.reply_photo(
                            photo=chart_buf,
                            caption=f"🏆 Топ активных пользователей\n🏷️ Группа: {group.title}"
                        )
                
            except Exception as e:
                logger.error(f"Ошибка генерации графиков: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации графиков: {e}")

        async def trend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Команда для получения графика динамики"""
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            await update.message.reply_text("📈 Генерирую график динамики...")
            
            try:
                # Получаем активные группы
                groups = await db.get_active_groups()
                if not groups:
                    await update.message.reply_text("❌ Нет активных групп для анализа")
                    return
                
                group = groups[0]  # Берём первую группу
                chart_gen = ChartGenerator()
                
                # Получаем данные динамики за 30 дней
                daily_trend = await db.get_daily_trend(group.group_id, days=30)
                
                if daily_trend and len(daily_trend) > 1:
                    chart_buf = chart_gen.create_daily_trend_chart(
                        daily_trend,
                        f"Динамика активности в группе '{group.title}'"
                    )
                    
                    if chart_buf:
                        await update.message.reply_photo(
                            photo=chart_buf,
                            caption=f"📈 Динамика активности за 30 дней\n🏷️ Группа: {group.title}\n📊 Данных: {len(daily_trend)} дней"
                        )
                else:
                    await update.message.reply_text("❌ Недостаточно данных для построения графика динамики (нужно минимум 2 дня)")
                
            except Exception as e:
                logger.error(f"Ошибка генерации графика динамики: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации графика: {e}")

        async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Команда для получения сводного дашборда"""
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            await update.message.reply_text("📊 Генерирую сводный дашборд...")
            
            try:
                # Получаем активные группы
                groups = await db.get_active_groups()
                if not groups:
                    await update.message.reply_text("❌ Нет активных групп для анализа")
                    return
                
                group = groups[0]  # Берём первую группу
                chart_gen = ChartGenerator()
                
                # Собираем все данные для дашборда
                summary_stats = await db.get_group_summary_stats(group.group_id)
                hourly_activity = await db.get_hourly_activity(group.group_id, days=7)
                top_users_data = await db.get_daily_stats(group.group_id, datetime.now())
                daily_trend = await db.get_daily_trend(group.group_id, days=14)
                
                # Объединяем данные
                dashboard_data = {
                    **summary_stats,
                    'hourly_activity': hourly_activity,
                    'top_users': top_users_data.get('top_users', []) if top_users_data else [],
                    'daily_trend': daily_trend
                }
                
                # Создаём дашборд
                chart_buf = chart_gen.create_summary_dashboard(
                    dashboard_data,
                    f"📊 Аналитическая панель - {group.title}"
                )
                
                if chart_buf:
                    await update.message.reply_photo(
                        photo=chart_buf,
                        caption=f"📊 Сводная аналитическая панель\n🏷️ Группа: {group.title}\n📈 Всего сообщений: {dashboard_data.get('total_messages', 0)}\n👥 Всего пользователей: {dashboard_data.get('total_users', 0)}"
                    )
                else:
                    await update.message.reply_text("❌ Ошибка создания дашборда")
                
            except Exception as e:
                logger.error(f"Ошибка генерации дашборда: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации дашборда: {e}")

        async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Команда для проверки алертов вручную"""
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            await update.message.reply_text("🚨 Проверяю алерты...")
            
            try:
                alert_system = AlertSystem(db, app.bot)
                alerts = await alert_system.check_all_groups()
                
                if alerts:
                    response = f"🚨 **НАЙДЕНО {len(alerts)} АЛЕРТОВ:**\n\n"
                    for i, alert in enumerate(alerts, 1):
                        response += f"{i}. **{alert.alert_type.upper()}**\n"
                        response += f"   Группа: {alert.group_name}\n"
                        response += f"   {alert.message}\n\n"
                        if len(response) > 3500:  # Telegram limit
                            await update.message.reply_text(response, parse_mode='Markdown')
                            response = "**Продолжение алертов:**\n\n"
                    
                    if len(response.strip()) > len("**Продолжение алертов:**"):
                        await update.message.reply_text(response, parse_mode='Markdown')
                else:
                    await update.message.reply_text("✅ Алертов не найдено - всё в порядке!")
                
            except Exception as e:
                logger.error(f"Ошибка проверки алертов: {e}")
                await update.message.reply_text(f"❌ Ошибка проверки алертов: {e}")

        async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Команда для экспорта данных в CSV"""
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            # Получаем параметр (тип экспорта)
            args = context.args
            export_type = args[0] if args else "full"
            
            await update.message.reply_text("📥 Экспортирую данные...")
            
            try:
                # Получаем активные группы
                groups = await db.get_active_groups()
                if not groups:
                    await update.message.reply_text("❌ Нет активных групп для экспорта")
                    return
                
                group = groups[0]  # Берём первую группу
                exporter = DataExporter(db)
                
                if export_type == "messages":
                    # Экспорт сообщений
                    csv_buffer = await exporter.export_messages_csv(group.group_id, 30)
                    if csv_buffer:
                        filename = f"{exporter.sanitize_filename(group.title)}_messages.csv"
                        await update.message.reply_document(
                            document=csv_buffer,
                            filename=filename,
                            caption=f"📄 Экспорт сообщений за 30 дней\n🏷️ Группа: {group.title}"
                        )
                    else:
                        await update.message.reply_text("❌ Ошибка экспорта сообщений")
                
                elif export_type == "users":
                    # Экспорт пользователей
                    csv_buffer = await exporter.export_users_csv(group.group_id)
                    if csv_buffer:
                        filename = f"{exporter.sanitize_filename(group.title)}_users.csv"
                        await update.message.reply_document(
                            document=csv_buffer,
                            filename=filename,
                            caption=f"👥 Экспорт пользователей\n🏷️ Группа: {group.title}"
                        )
                    else:
                        await update.message.reply_text("❌ Ошибка экспорта пользователей")
                
                elif export_type == "analytics":
                    # Экспорт аналитики
                    csv_buffer = await exporter.export_analytics_csv(group.group_id, 30)
                    if csv_buffer:
                        filename = f"{exporter.sanitize_filename(group.title)}_analytics.csv"
                        await update.message.reply_document(
                            document=csv_buffer,
                            filename=filename,
                            caption=f"📊 Экспорт дневной аналитики за 30 дней\n🏷️ Группа: {group.title}"
                        )
                    else:
                        await update.message.reply_text("❌ Ошибка экспорта аналитики")
                
                else:  # export_type == "full" или любой другой
                    # Полный экспорт
                    export_package = await exporter.create_full_export_package(
                        group.group_id, 
                        exporter.sanitize_filename(group.title)
                    )
                    
                    if export_package:
                        await update.message.reply_text(f"📦 Отправляю {len(export_package)} файлов...")
                        
                        for filename, file_buffer in export_package.items():
                            try:
                                await update.message.reply_document(
                                    document=file_buffer,
                                    filename=filename,
                                    caption=f"📁 {filename}\n🏷️ Группа: {group.title}"
                                )
                            except Exception as file_error:
                                logger.error(f"Ошибка отправки файла {filename}: {file_error}")
                        
                        await update.message.reply_text("✅ Экспорт завершён!")
                    else:
                        await update.message.reply_text("❌ Ошибка создания экспорта")
                
            except Exception as e:
                logger.error(f"Ошибка экспорта данных: {e}")
                await update.message.reply_text(f"❌ Ошибка экспорта: {e}")

        async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Команда для получения сводного отчёта"""
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            await update.message.reply_text("📊 Генерирую сводный отчёт...")
            
            try:
                # Получаем активные группы
                groups = await db.get_active_groups()
                if not groups:
                    await update.message.reply_text("❌ Нет активных групп для анализа")
                    return
                
                group = groups[0]  # Берём первую группу
                
                # Получаем данные
                summary_stats = await db.get_group_summary_stats(group.group_id)
                hourly_data = await db.get_hourly_activity(group.group_id, 7)
                daily_stats = await db.get_daily_stats(group.group_id, datetime.now())
                
                # Анализ пиков активности
                if hourly_data:
                    peak_hours = sorted(hourly_data.items(), key=lambda x: x[1], reverse=True)[:3]
                    peak_hours_text = ", ".join([f"{h}:00 ({c} сообщений)" for h, c in peak_hours])
                else:
                    peak_hours_text = "Данных недостаточно"
                
                # Формируем отчёт
                report = f"""
📊 **СВОДНЫЙ ОТЧЁТ ГРУППЫ**

🏷️ **Группа:** {summary_stats.get('group_name', 'Unknown')}
👥 **Участников:** {summary_stats.get('members_count', 0):,}

📈 **ОБЩАЯ СТАТИСТИКА:**
• Всего сообщений: {summary_stats.get('total_messages', 0):,}
• Уникальных пользователей: {summary_stats.get('total_users', 0):,}
• Среднее в день: {summary_stats.get('avg_daily', 0):.1f} сообщений

🏆 **АКТИВНОСТЬ:**
• Самый активный: {summary_stats.get('top_user', 'N/A')}
• Вовлечённость: {(summary_stats.get('total_users', 0) / max(summary_stats.get('members_count', 1), 1) * 100):.1f}%

⏰ **ПИКОВЫЕ ЧАСЫ:** 
{peak_hours_text}

📅 **СЕГОДНЯ:**
• Сообщений: {daily_stats.get('messages_count', 0)}
• Активных пользователей: {daily_stats.get('users_count', 0)}

💡 **РЕКОМЕНДАЦИИ:**
"""
                
                # Добавляем рекомендации на основе данных
                avg_daily = summary_stats.get('avg_daily', 0)
                if avg_daily < 10:
                    report += "• 🔥 Стимулируйте обсуждения - активность низкая\n"
                elif avg_daily > 100:
                    report += "• 📊 Отличная активность! Поддерживайте темп\n"
                
                engagement = summary_stats.get('total_users', 0) / max(summary_stats.get('members_count', 1), 1) * 100
                if engagement < 10:
                    report += "• 👥 Низкая вовлечённость - привлекайте участников\n"
                elif engagement > 30:
                    report += "• 🎯 Высокая вовлечённость - отличная работа!\n"
                
                report += f"\n📊 **Используйте:**\n• /charts - графики\n• /export - экспорт данных\n• /alerts - проверка алертов"
                
                await update.message.reply_text(report, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Ошибка генерации сводного отчёта: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации отчёта: {e}")

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
        app.add_handler(CommandHandler("groupinfo", groupinfo_command))
        app.add_handler(CommandHandler("addgroup", addgroup_command))
        app.add_handler(CommandHandler("debug", debug_command))
        app.add_handler(CommandHandler("testdb", testdb_command))
        
        # Новые команды с графиками
        app.add_handler(CommandHandler("charts", charts_command))
        app.add_handler(CommandHandler("trend", trend_command))
        app.add_handler(CommandHandler("dashboard", dashboard_command))
        app.add_handler(CommandHandler("alerts", alerts_command))
        app.add_handler(CommandHandler("export", export_command))
        app.add_handler(CommandHandler("summary", summary_command))
        
        # Обработчик сообщений в группах
        async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Обработка сообщений в группах для сбора аналитики"""
            if not update.message or not update.effective_chat:
                return
                
            chat = update.effective_chat
            message = update.message
            
            # Только для групп и супергрупп
            if chat.type not in ['group', 'supergroup']:
                return
            
            # Проверяем, что группа отслеживается
            if not db:
                return
                
            try:
                # Проверяем, что группа добавлена в систему мониторинга
                groups = await db.get_active_groups()
                group_ids = [g.group_id for g in groups]
                
                if chat.id not in group_ids:
                    return  # Группа не отслеживается
                
                # Собираем данные сообщения
                message_data = {
                    'message_id': message.message_id,
                    'group_id': chat.id,
                    'user_id': message.from_user.id if message.from_user else None,
                    'username': message.from_user.username if message.from_user else None,
                    'text': message.text or '',
                    'date': message.date,
                    'reply_to_message_id': message.reply_to_message.message_id if message.reply_to_message else None,
                    'forward_from_user_id': message.forward_from.id if message.forward_from else None,
                    'views': 0,  # Будет обновляться отдельно
                    'reactions': '{}'  # JSON для реакций
                }
                
                # Сохраняем в базу данных
                await db.save_messages([message_data])
                logger.debug(f"Сообщение {message.message_id} из группы {chat.id} сохранено")
                
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения из группы {chat.id}: {e}")
        
        # Добавляем обработчик сообщений
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_message))
        
        # Запуск бота
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        logger.info("✅ Telegram бот запущен успешно!")
        
        # Настройка планировщика
        if db and reports:
            try:
                # Создаём систему алертов
                alert_system = AlertSystem(db, app.bot)
                
                # Функции для автоматических отчетов
                def send_daily_reports():
                    asyncio.create_task(send_scheduled_reports(app, db, reports, 'daily'))
                
                def send_weekly_reports():
                    asyncio.create_task(send_scheduled_reports(app, db, reports, 'weekly'))
                
                # Функция для проверки алертов
                def check_alerts():
                    asyncio.create_task(alert_system.run_monitoring_cycle(config.admin_users))
                
                # Настройка расписания
                schedule.every().day.at("09:00").do(send_daily_reports)
                schedule.every().monday.at("09:00").do(send_weekly_reports)
                schedule.every(30).minutes.do(check_alerts)  # Проверка алертов каждые 30 минут
                
                # Запуск планировщика в отдельном потоке
                def run_scheduler():
                    nonlocal scheduler_running
                    scheduler_running = True
                    logger.info("✅ Планировщик запущен - отчеты и алерты будут отправляться автоматически")
                    logger.info("📅 Дневные отчеты: каждый день в 09:00")
                    logger.info("📅 Недельные отчеты: каждый понедельник в 09:00")
                    logger.info("🚨 Проверка алертов: каждые 30 минут")
                    
                    while app_running:
                        schedule.run_pending()
                        time.sleep(60)
                
                scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
                scheduler_thread.start()
                
            except Exception as e:
                logger.error(f"Ошибка настройки планировщика: {e}")
        else:
            logger.warning("⚠️  Планировщик не запущен (нет БД или системы отчетов)")
        
        # Поддержание работы
        while app_running:
            await asyncio.sleep(60)
            
    except ImportError as e:
        logger.warning(f"Telegram бот недоступен (нет зависимостей): {e}")
        logger.info("Работаю только как HTTP сервер")
        while app_running:
            await asyncio.sleep(60)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        logger.info("Продолжаю работать как HTTP сервер")
        while app_running:
            await asyncio.sleep(60)

async def main():
    """Главная функция"""
    global app_running, telegram_app
    
    def signal_handler(signum, frame):
        global app_running, telegram_app
        logger.info(f"Получен сигнал {signum}, начинаем graceful shutdown...")
        app_running = False
        if telegram_app:
            try:
                asyncio.create_task(telegram_app.stop())
                logger.info("Telegram bot остановлен")
            except Exception as e:
                logger.error(f"Ошибка остановки telegram bot: {e}")
        sys.exit(0)
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
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
