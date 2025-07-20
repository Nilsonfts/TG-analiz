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

# Telegram Bot API
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

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
            
            db = Database(config.database_url)
            await db.init_db()
            logger.info("✅ База данных подключена и инициализирована")
            
            # Создаем генератор отчетов если БД работает
            try:
                reports = ReportGenerator(db)
                logger.info("✅ Система отчетов инициализирована")
            except Exception as reports_error:
                logger.warning(f"⚠️  Ошибка инициализации отчетов: {reports_error}")
                
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
