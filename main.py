#!/usr/bin/env python3
"""
Telegram Analytics Bot - Управление несколькими группами с интерфейсом выбора
"""
import os
import http.server
import socketserver
import logging
import threading
import asyncio
import time
import signal
import sys
from datetime import datetime, timedelta

# Telegram Bot API
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# Наши модули
try:
    from visualization import ChartGenerator
except ImportError:
    ChartGenerator = None
    
try:
    from alerts import AlertSystem
except ImportError:
    AlertSystem = None
    
try:
    from data_export import DataExporter
except ImportError:
    DataExporter = None

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные
app_running = True
scheduler_running = False

class SimpleHttpHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        status = "🟢 Активен" if app_running else "🔴 Неактивен"
        scheduler_status = "🟢 Активен" if scheduler_running else "🔴 Неактивен"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Telegram Analytics Bot</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .status {{ padding: 20px; border-radius: 8px; margin: 10px 0; }}
                .active {{ background-color: #d4edda; color: #155724; }}
                .inactive {{ background-color: #f8d7da; color: #721c24; }}
            </style>
        </head>
        <body>
            <h1>🤖 Telegram Analytics Bot</h1>
            <div class="status {'active' if app_running else 'inactive'}">
                <h3>Статус бота: {status}</h3>
                <p>Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div class="status {'active' if scheduler_running else 'inactive'}">
                <h3>Планировщик: {scheduler_status}</h3>
                <p>Автоматические отчеты и алерты</p>
            </div>
            <h3>📊 Возможности бота:</h3>
            <ul>
                <li>✅ Управление несколькими группами</li>
                <li>✅ Интерфейс выбора групп через inline-клавиатуру</li>
                <li>✅ Дневные и недельные отчеты</li>
                <li>✅ Графики и визуализация активности</li>
                <li>✅ Система алертов и мониторинга</li>
                <li>✅ Экспорт данных в CSV</li>
                <li>✅ Аналитические дашборды</li>
            </ul>
            <h3>🔧 Команды бота:</h3>
            <ul>
                <li><code>/daily</code> - Дневной отчет (с выбором группы)</li>
                <li><code>/weekly</code> - Недельный отчет (с выбором группы)</li>
                <li><code>/charts</code> - Графики активности (с выбором группы)</li>
                <li><code>/trend</code> - График динамики (с выбором группы)</li>
                <li><code>/dashboard</code> - Сводная панель (с выбором группы)</li>
                <li><code>/export</code> - Экспорт данных (с выбором группы)</li>
                <li><code>/status</code> - Статус системы</li>
                <li><code>/help</code> - Помощь</li>
            </ul>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    global app_running
    logger.info(f"Получен сигнал {signum}, завершаю работу...")
    app_running = False
    sys.exit(0)

async def create_group_selection_keyboard(db, action_type: str):
    """Создание клавиатуры для выбора группы"""
    try:
        groups = await db.get_active_groups()
        if not groups:
            return None
        
        keyboard = []
        for group in groups:
            # Ограничиваем длину названия для кнопки
            title = group.title[:30] + "..." if len(group.title) > 30 else group.title
            callback_data = f"{action_type}:{group.group_id}"
            keyboard.append([InlineKeyboardButton(title, callback_data=callback_data)])
        
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        logger.error(f"Ошибка создания клавиатуры выбора групп: {e}")
        return None

async def handle_group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора группы из inline клавиатуры и графиков каналов"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Проверяем, это запрос графика канала или выбор группы
        if query.data.startswith("chart_"):
            # Обработка запросов графиков каналов
            chart_type = query.data.replace("chart_", "")
            
            channel_analytics = getattr(context.application, 'channel_analytics', None)
            if not channel_analytics:
                await query.message.reply_text("❌ Сервис аналитики каналов недоступен")
                return
            
            try:
                from channel_visualization import ChannelChartGenerator
                chart_gen = ChannelChartGenerator(channel_analytics)
                channel_id = -1001234567890  # Для демонстрации
                
                await query.edit_message_text("📊 Генерирую график...")
                
                chart_buf = None
                caption = ""
                
                if chart_type == "growth":
                    chart_buf = await chart_gen.generate_subscriber_growth_chart(channel_id, 30)
                    caption = "📈 График роста подписчиков за 30 дней"
                elif chart_type == "hourly":
                    chart_buf = await chart_gen.generate_hourly_activity_chart(channel_id, 7)
                    caption = "⏰ Почасовая активность аудитории за 7 дней"
                elif chart_type == "traffic":
                    chart_buf = await chart_gen.generate_traffic_sources_chart(channel_id, 30)
                    caption = "🎯 Источники трафика за 30 дней"
                elif chart_type == "engagement":
                    chart_buf = await chart_gen.generate_engagement_trends_chart(channel_id, 30)
                    caption = "📊 Тренды вовлеченности за 30 дней"
                elif chart_type == "dashboard":
                    chart_buf = await chart_gen.generate_dashboard_chart(channel_id)
                    caption = "🎛 Комплексный дашборд канала"
                
                if chart_buf:
                    await query.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=chart_buf,
                        caption=caption
                    )
                    await query.message.reply_text("✅ График успешно сгенерирован!")
                else:
                    await query.message.reply_text("❌ Не удалось сгенерировать график")
                    
            except ImportError:
                await query.message.reply_text("❌ Модуль визуализации недоступен")
            except Exception as e:
                logger.error(f"Ошибка генерации графика {chart_type}: {e}")
                await query.message.reply_text(f"❌ Ошибка генерации графика: {e}")
            
            return
        
        # Обработка выбора группы (старая логика)
        action, group_id = query.data.split(":", 1)
        group_id = int(group_id)
        
        # Получаем объекты из контекста приложения
        db = getattr(context.application, 'db', None)
        reports = getattr(context.application, 'reports', None)
        
        if not db:
            await query.message.reply_text("❌ База данных недоступна")
            return
        
        # Получаем информацию о группе
        group = await db.get_group_by_id(group_id)
        if not group:
            await query.message.reply_text("❌ Группа не найдена")
            return
        
        if action == "daily":
            # Дневной отчет для выбранной группы
            await query.message.reply_text(f"📊 Генерирую дневной отчет для группы '{group.title}'...")
            if reports:
                report = await reports.generate_daily_report(group_id)
                await query.message.reply_text(report, parse_mode='HTML')
            else:
                # Простой отчет без сервиса
                stats = await db.get_daily_stats(group_id, datetime.now() - timedelta(days=1))
                report = f"""📊 <b>Дневной отчет</b>

🏷️ Группа: {group.title}
📈 Сообщений: {stats.get('messages_count', 0)}
👥 Активных пользователей: {stats.get('users_count', 0)}
"""
                await query.message.reply_text(report, parse_mode='HTML')
        
        elif action == "weekly":
            # Недельный отчет для выбранной группы
            await query.message.reply_text(f"📈 Генерирую недельный отчет для группы '{group.title}'...")
            if reports:
                report = await reports.generate_weekly_report(group_id)
                await query.message.reply_text(report, parse_mode='HTML')
            else:
                # Простой отчет без сервиса
                start_date = datetime.now() - timedelta(days=7)
                stats = await db.get_weekly_stats(group_id, start_date.date())
                report = f"""📈 <b>Недельный отчет</b>

🏷️ Группа: {group.title}
📈 Сообщений за неделю: {stats.get('total_messages', 0)}
👥 Активных пользователей: {stats.get('total_active_users', 0)}
🆕 Новых участников: {stats.get('new_users', 0)}
"""
                await query.message.reply_text(report, parse_mode='HTML')
        
        elif action == "charts":
            # Графики для выбранной группы
            await query.message.reply_text(f"📊 Генерирую графики для группы '{group.title}'...")
            if ChartGenerator:
                chart_gen = ChartGenerator()
                
                # Получаем данные для графиков
                hourly_data = await db.get_hourly_activity(group_id, days=7)
                top_users_data = await db.get_top_users(group_id, days=7)
                
                # Создаём график активности по часам
                if hourly_data:
                    chart_buf = chart_gen.create_activity_chart(
                        hourly_data, 
                        f"Активность в группе '{group.title}' (7 дней)"
                    )
                    
                    if chart_buf:
                        await query.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=chart_buf,
                            caption=f"📊 График активности по часам\n🏷️ Группа: {group.title}\n📅 Период: 7 дней"
                        )
            else:
                await query.message.reply_text("❌ Модуль визуализации недоступен")
        
        elif action == "dashboard":
            # Дашборд для выбранной группы
            await query.message.reply_text(f"📊 Генерирую дашборд для группы '{group.title}'...")
            summary_stats = await db.get_group_summary_stats(group_id)
            
            report = f"""📊 <b>Сводная панель - {group.title}</b>

📈 <b>Общая статистика:</b>
• Всего сообщений: {summary_stats.get('total_messages', 0)}
• Всего пользователей: {summary_stats.get('total_users', 0)}
• Среднее в день: {summary_stats.get('avg_daily', 0):.1f}
• Топ пользователь: {summary_stats.get('top_user', 'N/A')}

👥 <b>Участники:</b>
• Количество: {summary_stats.get('members_count', 0)}

📅 <b>Период анализа:</b> {summary_stats.get('period', '30 дней')}
"""
            await query.message.reply_text(report, parse_mode='HTML')
        
        elif action == "export":
            # Экспорт данных для выбранной группы
            await query.message.reply_text(f"📥 Подготавливаю экспорт данных для группы '{group.title}'...")
            if DataExporter:
                exporter = DataExporter(db)
                
                # Полный экспорт
                export_package = await exporter.create_full_export_package(
                    group_id, 
                    exporter.sanitize_filename(group.title)
                )
                
                if export_package:
                    await query.message.reply_text(f"📦 Отправляю {len(export_package)} файлов для группы '{group.title}'...")
                    
                    for filename, file_buffer in export_package.items():
                        try:
                            await query.bot.send_document(
                                chat_id=query.message.chat_id,
                                document=file_buffer,
                                filename=filename,
                                caption=f"📁 {filename}\n🏷️ Группа: {group.title}"
                            )
                        except Exception as file_error:
                            logger.error(f"Ошибка отправки файла {filename}: {file_error}")
                    
                    await query.message.reply_text("✅ Экспорт завершён!")
                else:
                    await query.message.reply_text("❌ Ошибка создания экспорта")
            else:
                await query.message.reply_text("❌ Модуль экспорта недоступен")
        
        else:
            await query.message.reply_text(f"❌ Неизвестное действие: {action}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки callback: {e}")
        await query.message.reply_text(f"❌ Ошибка: {e}")

async def start_telegram_bot():
    """Запуск Telegram бота"""
    global app_running, scheduler_running
    
    try:
        from config import Config
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from database import Database
        from channel_analytics import ChannelAnalytics
        from channel_reports import ChannelReportService
        
        # Попытка импорта сервиса отчетов
        try:
            from services.report_service import ReportService
        except ImportError as e:
            logger.warning(f"Не удалось импортировать ReportService: {e}")
            ReportService = None
        
        logger.info("Инициализация Telegram бота...")
        
        # Загружаем конфигурацию
        config = Config()
        if not config.bot_token:
            logger.error("BOT_TOKEN не найден в переменных окружения!")
            logger.info("Работаю только как HTTP сервер")
            while app_running:
                await asyncio.sleep(60)
            return

        # Инициализация базы данных
        try:
            db = Database(config.database_url)
            await db.init_db()
            logger.info("✅ База данных подключена")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            db = None

        # Инициализация сервиса отчетов
        reports = None
        if ReportService:
            try:
                reports = ReportService()
                logger.info("✅ Сервис отчетов инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации сервиса отчетов: {e}")
                reports = None
        else:
            logger.warning("⚠️ Сервис отчетов недоступен - используются базовые отчеты")

        # Инициализация аналитики каналов
        channel_analytics = None
        channel_reports = None
        if db:
            try:
                channel_analytics = ChannelAnalytics(db)
                channel_reports = ChannelReportService(channel_analytics)
                logger.info("✅ Аналитика каналов инициализирована")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации аналитики каналов: {e}")
                channel_analytics = None
                channel_reports = None

        # Создание приложения
        application = Application.builder().token(config.bot_token).build()
        
        # Сохраняем объекты в контексте приложения
        application.db = db
        application.reports = reports
        application.channel_analytics = channel_analytics
        application.channel_reports = channel_reports

        # === КОМАНДЫ БОТА ===
        
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            await update.message.reply_text(
                f"📊 Привет! Я бот аналитики Telegram каналов.\n\n"
                f"🆔 Ваш ID: {user_id}\n\n"
                f"� Команды аналитики каналов:\n"
                f"• /summary - 📊 Сводная статистика канала\n"
                f"• /growth - 📈 Рост подписчиков\n"
                f"• /engagement - ⚡ Вовлеченность аудитории\n"
                f"• /traffic - 🎯 Источники трафика\n"
                f"• /recommendations - 🤖 AI-рекомендации\n\n"
                f"📊 Визуализация:\n"
                f"• /charts - 📈 Графики и диаграммы\n"
                f"• /export - 📁 Экспорт данных\n\n"
                f"⚙️ Система:\n"
                f"• /alerts - ⚠️ Проверка алертов\n"
                f"• /status - 💡 Статус системы\n"
                f"• /help - ❓ Подробная помощь\n\n"
                f"✨ Все отчеты содержат красивое форматирование с эмодзи!"
            )

        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            help_text = """
🤖 <b>Telegram Analytics Bot - Аналитика каналов</b>

� <b>Команды аналитики каналов:</b>
• /summary - 📊 Сводная статистика канала
• /growth - 📈 Рост и динамика подписчиков
• /engagement - ⚡ Вовлеченность аудитории
• /traffic - 🎯 Источники трафика и переходов
• /recommendations - 🤖 AI-рекомендации по улучшению
• /charts - 📊 Интерактивные графики и диаграммы

⚙️ <b>Системные команды:</b>
• /alerts - ⚠️ Проверка системных алертов
• /status - 💡 Статус системы и подключений
• /help - ❓ Эта подробная справка

� <b>Особенности отчетов:</b>
• ✨ Красивое форматирование с эмодзи
• 📊 Детальная аналитика с AI-рекомендациями
• 📈 Интерактивные графики по запросу
• �🎯 Анализ источников трафика
• ⏰ Оптимальное время публикации

💡 <b>Как использовать:</b>
1. Выберите команду аналитики (например, /summary)
2. Получите красиво оформленный отчет с эмодзи
3. Используйте /charts для визуальной аналитики
4. Следуйте AI-рекомендациям для роста канала

� <b>Для лучших результатов:</b>
• Регулярно проверяйте /growth для отслеживания динамики
• Анализируйте /engagement для оптимизации контента
• Изучайте /traffic для понимания источников аудитории
• Применяйте /recommendations для стратегического развития
"""
            await update.message.reply_text(help_text, parse_mode='HTML')

        async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return

            db_status = "🟢 Подключена" if db else "🔴 Недоступна"
            reports_status = "🟢 Активен" if reports else "🔴 Недоступен"
            scheduler_status = "🟢 Запущен" if scheduler_running else "🔴 Остановлен"
            
            groups_count = 0
            if db:
                try:
                    groups = await db.get_active_groups()
                    groups_count = len(groups)
                except:
                    pass

            status_text = f"""
📊 <b>Статус Telegram Analytics Bot</b>

🗄️ <b>База данных:</b> {db_status}
📈 <b>Сервис отчетов:</b> {reports_status}
⏰ <b>Планировщик:</b> {scheduler_status}

📋 <b>Статистика:</b>
• Активных групп: {groups_count}
• Администраторов: {len(config.admin_users)}

🕐 <b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            await update.message.reply_text(status_text, parse_mode='HTML')

        async def daily_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            # Создаем клавиатуру выбора группы
            keyboard = await create_group_selection_keyboard(db, "daily")
            if not keyboard:
                await update.message.reply_text("❌ Нет активных групп для мониторинга")
                return
            
            await update.message.reply_text(
                "📊 Выберите группу для дневного отчета:",
                reply_markup=keyboard
            )

        async def weekly_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            # Создаем клавиатуру выбора группы
            keyboard = await create_group_selection_keyboard(db, "weekly")
            if not keyboard:
                await update.message.reply_text("❌ Нет активных групп для мониторинга")
                return
            
            await update.message.reply_text(
                "📈 Выберите группу для недельного отчета:",
                reply_markup=keyboard
            )

        async def charts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            # Создаем клавиатуру выбора группы
            keyboard = await create_group_selection_keyboard(db, "charts")
            if not keyboard:
                await update.message.reply_text("❌ Нет активных групп для анализа")
                return
            
            await update.message.reply_text(
                "📊 Выберите группу для графиков активности:",
                reply_markup=keyboard
            )

        async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            # Создаем клавиатуру выбора группы
            keyboard = await create_group_selection_keyboard(db, "dashboard")
            if not keyboard:
                await update.message.reply_text("❌ Нет активных групп для анализа")
                return
            
            await update.message.reply_text(
                "📊 Выберите группу для сводного дашборда:",
                reply_markup=keyboard
            )

        async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            
            # Проверяем права администратора
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут использовать эту команду!")
                return
            
            if not db:
                await update.message.reply_text("❌ База данных недоступна")
                return
            
            # Создаем клавиатуру выбора группы
            keyboard = await create_group_selection_keyboard(db, "export")
            if not keyboard:
                await update.message.reply_text("❌ Нет активных групп для экспорта")
                return
            
            await update.message.reply_text(
                "📥 Выберите группу для экспорта данных:",
                reply_markup=keyboard
            )

        # === КОМАНДЫ ДЛЯ АНАЛИТИКИ КАНАЛОВ ===
        
        async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Сводная статистика канала"""
            if not channel_reports:
                await update.message.reply_text("❌ Сервис аналитики каналов недоступен")
                return
            
            # Для демонстрации используем фиксированный ID канала
            # В реальном проекте здесь будет выбор канала
            channel_id = -1001234567890  # Примерный ID канала
            
            try:
                report = await channel_reports.generate_channel_summary_report(channel_id)
                await update.message.reply_text(report, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Ошибка генерации сводного отчета: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации отчета: {e}")

        async def growth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Отчет роста подписчиков"""
            if not channel_reports:
                await update.message.reply_text("❌ Сервис аналитики каналов недоступен")
                return
            
            channel_id = -1001234567890
            
            try:
                report = await channel_reports.generate_growth_report(channel_id)
                await update.message.reply_text(report, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Ошибка генерации отчета роста: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации отчета: {e}")

        async def engagement_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Отчет вовлеченности аудитории"""
            if not channel_reports:
                await update.message.reply_text("❌ Сервис аналитики каналов недоступен")
                return
            
            channel_id = -1001234567890
            
            try:
                report = await channel_reports.generate_engagement_report(channel_id)
                await update.message.reply_text(report, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Ошибка генерации отчета вовлеченности: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации отчета: {e}")

        async def traffic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Отчет источников трафика"""
            if not channel_reports:
                await update.message.reply_text("❌ Сервис аналитики каналов недоступен")
                return
            
            channel_id = -1001234567890
            
            try:
                report = await channel_reports.generate_traffic_report(channel_id)
                await update.message.reply_text(report, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Ошибка генерации отчета трафика: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации отчета: {e}")

        async def recommendations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """AI-рекомендации для канала"""
            if not channel_reports:
                await update.message.reply_text("❌ Сервис аналитики каналов недоступен")
                return
            
            channel_id = -1001234567890
            
            try:
                report = await channel_reports.generate_recommendations_report(channel_id)
                await update.message.reply_text(report, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Ошибка генерации AI-рекомендаций: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации отчета: {e}")

        async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Проверка алертов"""
            user_id = update.effective_user.id
            
            if user_id not in config.admin_users:
                await update.message.reply_text("❌ Только администраторы могут проверять алерты!")
                return
            
            try:
                if AlertSystem:
                    alert_system = AlertSystem(db)
                    alerts = await alert_system.check_all_alerts()
                    if alerts:
                        alert_text = "⚠️ <b>АКТИВНЫЕ АЛЕРТЫ:</b>\n\n"
                        for alert in alerts:
                            alert_text += f"• {alert}\n"
                        await update.message.reply_text(alert_text, parse_mode='HTML')
                    else:
                        await update.message.reply_text("✅ Все системы работают нормально!")
                else:
                    await update.message.reply_text("❌ Система алертов недоступна")
            except Exception as e:
                logger.error(f"Ошибка проверки алертов: {e}")
                await update.message.reply_text(f"❌ Ошибка проверки алертов: {e}")

        async def channel_charts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Генерация графиков для канала"""
            if not channel_analytics:
                await update.message.reply_text("❌ Сервис аналитики каналов недоступен")
                return
            
            try:
                from channel_visualization import ChannelChartGenerator
                chart_gen = ChannelChartGenerator(channel_analytics)
                
                channel_id = -1001234567890  # Для демонстрации
                
                await update.message.reply_text("📊 Генерирую графики канала...")
                
                # Создаем клавиатуру выбора типа графика
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📈 Рост подписчиков", callback_data="chart_growth"),
                        InlineKeyboardButton("⏰ Активность по часам", callback_data="chart_hourly")
                    ],
                    [
                        InlineKeyboardButton("🎯 Источники трафика", callback_data="chart_traffic"),
                        InlineKeyboardButton("📊 Тренды вовлеченности", callback_data="chart_engagement")
                    ],
                    [
                        InlineKeyboardButton("🎛 Полный дашборд", callback_data="chart_dashboard")
                    ]
                ])
                
                await update.message.reply_text(
                    "📈 <b>Выберите тип графика:</b>\n\n"
                    "• 📈 Рост подписчиков - динамика за последние 30 дней\n"
                    "• ⏰ Активность по часам - оптимальное время публикации\n"
                    "• 🎯 Источники трафика - откуда приходят подписчики\n"
                    "• 📊 Тренды вовлеченности - анализ реакций аудитории\n"
                    "• 🎛 Полный дашборд - комплексная аналитика",
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                
            except ImportError:
                await update.message.reply_text("❌ Модуль визуализации недоступен")
            except Exception as e:
                logger.error(f"Ошибка команды графиков: {e}")
                await update.message.reply_text(f"❌ Ошибка генерации графиков: {e}")

        # Регистрация обработчиков команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        
        # Команды аналитики каналов
        application.add_handler(CommandHandler("summary", summary_command))
        application.add_handler(CommandHandler("growth", growth_command))
        application.add_handler(CommandHandler("engagement", engagement_command))
        application.add_handler(CommandHandler("traffic", traffic_command))
        application.add_handler(CommandHandler("recommendations", recommendations_command))
        application.add_handler(CommandHandler("alerts", alerts_command))
        application.add_handler(CommandHandler("charts", channel_charts_command))
        
        # Старые команды (оставляем для совместимости)
        application.add_handler(CommandHandler("daily", daily_report_command))
        application.add_handler(CommandHandler("weekly", weekly_report_command))
        application.add_handler(CommandHandler("charts", charts_command))
        application.add_handler(CommandHandler("dashboard", dashboard_command))
        application.add_handler(CommandHandler("export", export_command))
        
        # Обработчик callback queries (выбор групп)
        application.add_handler(CallbackQueryHandler(handle_group_callback))

        # Запуск бота
        logger.info("🚀 Запускаю Telegram бота...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        logger.info("✅ Telegram бот успешно запущен и готов к работе!")
        logger.info("🎯 Поддерживается управление несколькими группами через inline-клавиатуру")
        
        # Поддержание работы
        while app_running:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в Telegram боте: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if 'application' in locals():
                await application.stop()
                await application.shutdown()
            if db:
                await db.close()
        except Exception as e:
            logger.error(f"Ошибка при завершении: {e}")

def start_http_server():
    """Запуск HTTP сервера"""
    try:
        port = int(os.environ.get('PORT', 8000))
        
        # Создаем HTTP сервер
        httpd = socketserver.TCPServer(("", port), SimpleHttpHandler)
        httpd.allow_reuse_address = True
        
        logger.info(f"🌐 HTTP сервер запущен на порту {port}")
        httpd.serve_forever()
        
    except Exception as e:
        logger.error(f"❌ Ошибка HTTP сервера: {e}")

async def main():
    """Главная функция"""
    global app_running
    
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("🚀 Запуск Telegram Analytics Bot")
    logger.info("🎯 Версия: Управление несколькими группами с inline-клавиатурой")
    
    # Запуск HTTP сервера в отдельном потоке
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    # Запуск Telegram бота
    try:
        await start_telegram_bot()
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        app_running = False
        logger.info("👋 Telegram Analytics Bot завершил работу")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа прервана пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {e}")
