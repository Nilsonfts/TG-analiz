import asyncio
import logging
import os
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
import schedule
import time
import threading
from aiohttp import web
import aiohttp_cors

from config import Config
from database import Database, TelegramGroup, UserSubscription
from analytics import AnalyticsCollector
from reports import ReportGenerator

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramAnalyticsBot:
    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.database_url)
        self.analytics = AnalyticsCollector(self.config, self.db)
        self.reports = ReportGenerator(self.db)
        self.app = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        welcome_text = """
🚀 Добро пожаловать в Telegram Analytics Bot!

Доступные команды:
/help - показать помощь
/daily - получить дневной отчет
/weekly - получить недельный отчет
/monthly - получить месячный отчет
/subscribe daily|weekly|monthly - подписаться на отчеты
/unsubscribe daily|weekly|monthly - отписаться от отчетов
/groups - показать отслеживаемые группы
        """
        
        if user_id in self.config.admin_users:
            welcome_text += """
👑 Команды администратора:
/add_group <group_id> - добавить группу для мониторинга
/remove_group <group_id> - удалить группу из мониторинга
/stats - показать общую статистику
            """
        
        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        await self.start_command(update, context)

    async def daily_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка дневного отчета"""
        try:
            report = await self.reports.generate_daily_report()
            await update.message.reply_text(report, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка при генерации дневного отчета: {e}")
            await update.message.reply_text("Ошибка при генерации отчета")

    async def weekly_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка недельного отчета"""
        try:
            report = await self.reports.generate_weekly_report()
            await update.message.reply_text(report, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка при генерации недельного отчета: {e}")
            await update.message.reply_text("Ошибка при генерации отчета")

    async def monthly_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка месячного отчета"""
        try:
            report = await self.reports.generate_monthly_report()
            await update.message.reply_text(report, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка при генерации месячного отчета: {e}")
            await update.message.reply_text("Ошибка при генерации отчета")

    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подписка на отчеты"""
        if not context.args:
            await update.message.reply_text("Укажите тип отчета: daily, weekly или monthly")
            return
            
        report_type = context.args[0].lower()
        if report_type not in ['daily', 'weekly', 'monthly']:
            await update.message.reply_text("Доступные типы: daily, weekly, monthly")
            return
            
        user_id = update.effective_user.id
        await self.db.subscribe_user(user_id, report_type)
        await update.message.reply_text(f"Вы подписались на {report_type} отчеты!")

    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отписка от отчетов"""
        if not context.args:
            await update.message.reply_text("Укажите тип отчета: daily, weekly или monthly")
            return
            
        report_type = context.args[0].lower()
        user_id = update.effective_user.id
        await self.db.unsubscribe_user(user_id, report_type)
        await update.message.reply_text(f"Вы отписались от {report_type} отчетов!")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Exception while handling an update: {context.error}")

    def collect_analytics_job(self):
        """Задача для сбора аналитики"""
        asyncio.run(self.analytics.collect_all_data())

    def send_daily_reports_job(self):
        """Отправка дневных отчетов подписчикам"""
        asyncio.run(self.send_scheduled_reports('daily'))

    def send_weekly_reports_job(self):
        """Отправка недельных отчетов подписчикам"""
        asyncio.run(self.send_scheduled_reports('weekly'))

    def send_monthly_reports_job(self):
        """Отправка месячных отчетов подписчикам"""
        asyncio.run(self.send_scheduled_reports('monthly'))

    async def send_scheduled_reports(self, report_type: str):
        """Отправка запланированных отчетов"""
        try:
            subscribers = await self.db.get_subscribers(report_type)
            
            if report_type == 'daily':
                report = await self.reports.generate_daily_report()
            elif report_type == 'weekly':
                report = await self.reports.generate_weekly_report()
            else:
                report = await self.reports.generate_monthly_report()
            
            for user_id in subscribers:
                try:
                    await self.app.bot.send_message(
                        chat_id=user_id,
                        text=report,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки отчета пользователю {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка при отправке {report_type} отчетов: {e}")

    def schedule_jobs(self):
        """Настройка расписания задач"""
        # Сбор аналитики каждый час
        schedule.every().hour.do(self.collect_analytics_job)
        
        # Отправка отчетов
        schedule.every().day.at("09:00").do(self.send_daily_reports_job)
        schedule.every().monday.at("09:00").do(self.send_weekly_reports_job)
        schedule.every().month.do(self.send_monthly_reports_job)
        
        logger.info("Планировщик задач настроен")

    def run_scheduler(self):
        """Запуск планировщика в отдельном потоке"""
        while True:
            schedule.run_pending()
            time.sleep(60)

    async def health_check(self, request):
        """Health check endpoint для Railway"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'bot_running': True
        })

    async def root_handler(self, request):
        """Root endpoint"""
        return web.Response(text="Telegram Analytics Bot is running")

    async def start_web_server(self):
        """Запуск веб-сервера для health checks"""
        app = web.Application()
        
        # Настройка CORS
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Добавление маршрутов
        app.router.add_get('/', self.root_handler)
        app.router.add_get('/health', self.health_check)
        
        # Применение CORS
        for route in list(app.router.routes()):
            cors.add(route)
        
        # Запуск сервера
        port = int(os.getenv('PORT', 8000))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"HTTP сервер запущен на порту {port}")

    async def run(self):
        """Основной метод запуска бота"""
        try:
            # Инициализация базы данных
            await self.db.init_db()
            logger.info("База данных инициализирована")
            
            # Создание приложения бота
            self.app = Application.builder().token(self.config.bot_token).build()
            
            # Регистрация обработчиков команд
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("help", self.help_command))
            self.app.add_handler(CommandHandler("daily", self.daily_report))
            self.app.add_handler(CommandHandler("weekly", self.weekly_report))
            self.app.add_handler(CommandHandler("monthly", self.monthly_report))
            self.app.add_handler(CommandHandler("subscribe", self.subscribe_command))
            self.app.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
            
            # Обработчик ошибок
            self.app.add_error_handler(self.error_handler)
            
            logger.info("Бот инициализирован успешно")
            
            # Настройка планировщика
            self.schedule_jobs()
            scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("Планировщик запущен")
            
            # Запуск веб-сервера
            await self.start_web_server()
            
            # Запуск бота
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            logger.info("Бот запущен и работает")
            
            # Поддержание работы
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            raise

async def main():
    """Точка входа"""
    bot = TelegramAnalyticsBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
        await self.application.updater.start_polling()
        
        logger.info("Бот запущен и работает...")
        
        try:
            # Ожидание завершения
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Корректное завершение работы бота"""
        logger.info("Завершение работы бота...")
        
        try:
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            
            if self.telethon_client:
                await self.telethon_client.disconnect()
            
            if self.web_runner:
                await self.web_runner.cleanup()
                
        except Exception as e:
            ErrorHandler.log_error(e, "Bot shutdown")
        
        logger.info("Бот завершен")

def main():
    """Главная функция для запуска бота"""
    bot = TelegramAnalyticsBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
