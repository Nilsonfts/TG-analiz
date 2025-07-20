import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from telethon import TelegramClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from dotenv import load_dotenv
from aiohttp import web
import aiohttp
import threading

from database.models import init_db
from services.analytics_service import AnalyticsService
from services.report_service import ReportService
from services.scheduler_service import SchedulerService
from handlers.commands import (
    start_command, daily_command, weekly_command, monthly_command,
    summary_command, subscribe_command, unsubscribe_command, help_command
)
from utils.auth import is_admin
from utils.health import health_checker, setup_error_logging, ErrorHandler

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
setup_error_logging()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramAnalyticsBot:
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.api_id = int(os.getenv('API_ID'))
        self.api_hash = os.getenv('API_HASH')
        self.timezone = pytz.timezone(os.getenv('TIMEZONE', 'Europe/Moscow'))
        self.port = int(os.getenv('PORT', 8000))
        
        # Инициализация сервисов
        self.analytics_service = AnalyticsService()
        self.report_service = ReportService()
        self.scheduler_service = SchedulerService()
        
        # Telethon клиент для работы с API
        self.telethon_client = TelegramClient(
            'session',
            self.api_id,
            self.api_hash
        )
        
        # Telegram Bot API
        self.application = None
        
        # HTTP сервер для health checks
        self.web_app = None
        self.web_runner = None

    async def initialize(self):
        """Инициализация бота и базы данных"""
        try:
            # Инициализация базы данных
            await init_db()
            
            # Создание приложения бота
            self.application = Application.builder().token(self.bot_token).build()
            
            # Регистрация команд
            await self.register_commands()
            
            # Запуск Telethon клиента
            await self.telethon_client.start()
            
            # Настройка планировщика
            await self.setup_scheduler()
            
            # Настройка HTTP сервера
            await self.setup_web_server()
            
            logger.info("Бот инициализирован успешно")
            
        except Exception as e:
            ErrorHandler.log_error(e, "Bot initialization")
            raise

    async def register_commands(self):
        """Регистрация команд бота"""
        commands = [
            CommandHandler("start", start_command),
            CommandHandler("help", help_command),
            CommandHandler("daily", daily_command),
            CommandHandler("weekly", weekly_command),
            CommandHandler("monthly", monthly_command),
            CommandHandler("summary", summary_command),
            CommandHandler("subscribe", subscribe_command),
            CommandHandler("unsubscribe", unsubscribe_command),
        ]
        
        for command in commands:
            self.application.add_handler(command)
        
        # Установка меню команд
        bot_commands = [
            BotCommand("start", "Запуск бота"),
            BotCommand("help", "Справка по командам"),
            BotCommand("daily", "Ежедневный отчёт"),
            BotCommand("weekly", "Еженедельный отчёт"),
            BotCommand("monthly", "Ежемесячный отчёт"),
            BotCommand("summary", "Отчёт за конкретную дату"),
            BotCommand("subscribe", "Подписка на отчёты"),
            BotCommand("unsubscribe", "Отмена подписки"),
        ]
        
        await self.application.bot.set_my_commands(bot_commands)

    async def setup_scheduler(self):
        """Настройка планировщика задач"""
        scheduler = AsyncIOScheduler(timezone=self.timezone)
        
        # Ежедневные отчеты в 09:00
        scheduler.add_job(
            self.send_daily_reports,
            CronTrigger(hour=9, minute=0, timezone=self.timezone),
            id='daily_reports'
        )
        
        # Еженедельные отчеты в понедельник в 09:00
        scheduler.add_job(
            self.send_weekly_reports,
            CronTrigger(day_of_week=0, hour=9, minute=0, timezone=self.timezone),
            id='weekly_reports'
        )
        
        # Ежемесячные отчеты 1 числа в 09:00
        scheduler.add_job(
            self.send_monthly_reports,
            CronTrigger(day=1, hour=9, minute=0, timezone=self.timezone),
            id='monthly_reports'
        )
        
        # Сбор данных каждый час
        scheduler.add_job(
            self.collect_analytics_data,
            CronTrigger(minute=0, timezone=self.timezone),
            id='collect_data'
        )
        
        scheduler.start()
        logger.info("Планировщик запущен")

    async def setup_web_server(self):
        """Настройка HTTP сервера для health checks"""
        self.web_app = web.Application()
        self.web_app.router.add_get('/health', self.health_check)
        self.web_app.router.add_get('/', self.root_handler)
        
        self.web_runner = web.AppRunner(self.web_app)
        await self.web_runner.setup()
        
        site = web.TCPSite(self.web_runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"HTTP сервер запущен на порту {self.port}")

    async def health_check(self, request):
        """Health check endpoint"""
        try:
            health_status = await health_checker.perform_health_check()
            
            if health_status['status'] == 'healthy':
                return web.Response(text="OK", status=200)
            else:
                return web.json_response(health_status, status=503)
                
        except Exception as e:
            ErrorHandler.log_error(e, "Health check")
            return web.Response(text="Health check failed", status=503)

    async def root_handler(self, request):
        """Корневой endpoint"""
        return web.Response(
            text="Telegram Analytics Bot is running", 
            status=200
        )

    async def collect_analytics_data(self):
        """Сбор аналитических данных"""
        try:
            await self.analytics_service.collect_data(self.telethon_client)
            logger.info("Данные аналитики собраны успешно")
        except Exception as e:
            ErrorHandler.log_error(e, "Analytics data collection")

    async def send_daily_reports(self):
        """Отправка ежедневных отчетов"""
        try:
            subscribers = await self.scheduler_service.get_daily_subscribers()
            for subscriber in subscribers:
                try:
                    report = await self.report_service.generate_daily_report()
                    await self.application.bot.send_message(
                        chat_id=subscriber['chat_id'],
                        text=report['text'],
                        parse_mode='HTML'
                    )
                    if report.get('chart'):
                        await self.application.bot.send_photo(
                            chat_id=subscriber['chat_id'],
                            photo=report['chart']
                        )
                except Exception as e:
                    ErrorHandler.log_error(e, f"Sending daily report to {subscriber['chat_id']}")
            logger.info("Ежедневные отчеты отправлены")
        except Exception as e:
            ErrorHandler.log_error(e, "Daily reports sending")

    async def send_weekly_reports(self):
        """Отправка еженедельных отчетов"""
        try:
            subscribers = await self.scheduler_service.get_weekly_subscribers()
            for subscriber in subscribers:
                try:
                    report = await self.report_service.generate_weekly_report()
                    await self.application.bot.send_message(
                        chat_id=subscriber['chat_id'],
                        text=report['text'],
                        parse_mode='HTML'
                    )
                    if report.get('chart'):
                        await self.application.bot.send_photo(
                            chat_id=subscriber['chat_id'],
                            photo=report['chart']
                        )
                except Exception as e:
                    ErrorHandler.log_error(e, f"Sending weekly report to {subscriber['chat_id']}")
            logger.info("Еженедельные отчеты отправлены")
        except Exception as e:
            ErrorHandler.log_error(e, "Weekly reports sending")

    async def send_monthly_reports(self):
        """Отправка ежемесячных отчетов"""
        try:
            subscribers = await self.scheduler_service.get_monthly_subscribers()
            for subscriber in subscribers:
                try:
                    report = await self.report_service.generate_monthly_report()
                    await self.application.bot.send_message(
                        chat_id=subscriber['chat_id'],
                        text=report['text'],
                        parse_mode='HTML'
                    )
                    if report.get('chart'):
                        await self.application.bot.send_photo(
                            chat_id=subscriber['chat_id'],
                            photo=report['chart']
                        )
                except Exception as e:
                    ErrorHandler.log_error(e, f"Sending monthly report to {subscriber['chat_id']}")
            logger.info("Ежемесячные отчеты отправлены")
        except Exception as e:
            ErrorHandler.log_error(e, "Monthly reports sending")

    async def run(self):
        """Запуск бота"""
        await self.initialize()
        
        # Запуск polling
        await self.application.initialize()
        await self.application.start()
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
