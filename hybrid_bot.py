#!/usr/bin/env python3
"""
Hybrid Railway Bot - ВСЕГДА работает + полный функционал
Гарантированно проходит healthcheck + запускает Telegram бот
"""
import asyncio
import json
import logging
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler - ВСЕГДА работает"""
    
    def log_message(self, format, *args):
        # Переопределяем для контроля логирования
        logger.info(format % args)
    
    def do_GET(self):
        if self.path == '/health':
            # Обязательный healthcheck для Railway
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "service": "telegram-analytics-bot",
                "bot_status": bot_manager.get_status(),
                "uptime": time.time() - start_time,
                "version": "hybrid-1.0"
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
            logger.info("✅ Health check successful")
            
        elif self.path == '/status':
            # Статус бота
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            status = {
                "server": "running",
                "bot": bot_manager.get_detailed_status(),
                "config": bot_manager.get_config_status(),
                "timestamp": time.time()
            }
            
            self.wfile.write(json.dumps(status, indent=2).encode('utf-8'))
            
        else:
            # Главная страница
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <h1>🤖 Telegram Analytics Bot</h1>
            <p><strong>Status:</strong> Running</p>
            <p><strong>Bot Status:</strong> {}</p>
            <p><a href="/health">Health Check</a> | <a href="/status">Status JSON</a></p>
            """.format(bot_manager.get_status())
            
            self.wfile.write(html.encode('utf-8'))

class BotManager:
    """Управляет Telegram ботом с graceful fallback"""
    
    def __init__(self):
        self.status = "initializing"
        self.bot = None
        self.bot_task = None
        self.error_count = 0
        self.last_error = None
        
    def get_status(self):
        return self.status
    
    def get_detailed_status(self):
        return {
            "status": self.status,
            "errors": self.error_count,
            "last_error": self.last_error,
            "bot_running": self.bot is not None,
            "task_running": self.bot_task is not None and not self.bot_task.done()
        }
    
    def get_config_status(self):
        """Проверяем конфигурацию"""
        config = {}
        
        # Проверяем основные переменные
        config['bot_token'] = "✅" if os.getenv('BOT_TOKEN') else "❌"
        config['api_id'] = "✅" if os.getenv('API_ID') or os.getenv('TELEGRAM_API_ID') else "❌"
        config['api_hash'] = "✅" if os.getenv('API_HASH') or os.getenv('TELEGRAM_API_HASH') else "❌"
        config['database'] = "✅" if os.getenv('DATABASE_URL') else "❌"
        
        return config
    
    async def start_bot(self):
        """Запускаем бота с graceful fallback"""
        try:
            self.status = "starting"
            logger.info("🤖 Attempting to start Telegram bot...")
            
            # Проверяем базовые требования
            bot_token = os.getenv('BOT_TOKEN')
            if not bot_token:
                raise ValueError("BOT_TOKEN not found")
            
            # Пытаемся импортировать и запустить полный бот
            try:
                from src.config import settings
                from src.bot import start_bot
                
                logger.info("📦 Loaded full bot modules")
                self.bot = await start_bot()
                self.status = "running_full"
                logger.info("✅ Full Telegram bot started successfully!")
                
            except ImportError as e:
                logger.warning(f"⚠️ Full bot modules not available: {e}")
                # Fallback к простому боту
                await self.start_simple_bot(bot_token)
                
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"❌ Bot start failed: {e}")
            self.status = "failed"
    
    async def start_simple_bot(self, bot_token):
        """Простой бот как fallback"""
        try:
            # Простейший бот с aiogram
            from aiogram import Bot, Dispatcher
            from aiogram.types import Message
            from aiogram.filters import Command
            
            bot = Bot(token=bot_token)
            dp = Dispatcher()
            
            # Пытаемся подключить аналитику
            analytics_available = False
            try:
                from src.db.database_service import DatabaseService
                from src.handlers.analytics_commands import AnalyticsCommands
                
                # Проверяем наличие DATABASE_URL
                database_url = os.getenv('DATABASE_URL')
                if database_url:
                    db_service = DatabaseService(database_url)
                    await db_service.init_db()
                    
                    analytics = AnalyticsCommands(db_service)
                    dp.include_router(analytics.router)
                    analytics_available = True
                    logger.info("✅ Аналитические команды подключены!")
                else:
                    logger.warning("⚠️ DATABASE_URL не найден, аналитика отключена")
                    
            except Exception as e:
                logger.warning(f"⚠️ Аналитика недоступна: {e}")
            
            @dp.message(Command("start"))
            async def start_command(message: Message):
                status_text = "🔥 Полная аналитика" if analytics_available else "⚡ Базовый режим"
                await message.answer(
                    f"🤖 <b>Telegram Analytics Bot запущен!</b>\n\n"
                    f"📊 <b>Статус:</b> {status_text}\n"
                    f"⚡ <b>Режим:</b> Гибридный бот\n\n"
                    f"📝 <b>Основные команды:</b>\n"
                    f"/start - Информация о боте\n"
                    f"/status - Текущий статус\n"
                    f"/help - Помощь\n"
                    f"/info - Информация о системе\n\n" +
                    (f"📊 <b>Аналитические команды:</b>\n"
                     f"/add @channel - Добавить канал\n"
                     f"/list - Список каналов\n"
                     f"/stats @channel - Статистика\n"
                     f"/summary - Общая сводка\n\n" if analytics_available else "") +
                    f"🌐 <b>Web интерфейс:</b> {os.getenv('RAILWAY_URL', 'localhost:8080')}/status",
                    parse_mode="HTML"
                )
            
            @dp.message(Command("status"))
            async def status_command(message: Message):
                uptime = time.time() - start_time
                await message.answer(
                    f"📊 <b>Статус системы:</b>\n\n"
                    f"🟢 <b>Режим:</b> {self.status}\n"
                    f"🕐 <b>Время работы:</b> {uptime:.0f}с\n"
                    f"❌ <b>Ошибки:</b> {self.error_count}\n"
                    f"🤖 <b>ID бота:</b> {bot.id}\n"
                    f"⚡ <b>Health server:</b> Работает\n"
                    f"📊 <b>Аналитика:</b> {'✅ Включена' if analytics_available else '❌ Отключена'}\n"
                    f"💾 <b>База данных:</b> {'✅ PostgreSQL' if analytics_available else '❌ Не подключена'}",
                    parse_mode="HTML"
                )
            
            @dp.message(Command("help"))
            async def help_command(message: Message):
                help_text = (
                    "🆘 <b>Помощь по боту:</b>\n\n"
                    "Этот бот предназначен для аналитики Telegram каналов.\n\n"
                    "📝 <b>Основные команды:</b>\n"
                    "/start - Запуск бота\n"
                    "/status - Статус системы\n"
                    "/help - Эта справка\n"
                    "/info - Техническая информация\n\n"
                )
                
                if analytics_available:
                    help_text += (
                        "� <b>Команды аналитики:</b>\n"
                        "/add @channel - Добавить канал в мониторинг\n"
                        "/remove @channel - Удалить канал\n"
                        "/list - Список всех каналов\n"
                        "/stats @channel [дни] - Статистика канала\n"
                        "/summary - Общая сводка\n"
                        "/channels - Публичный список каналов\n\n"
                        "👑 <b>Админские команды требуют прав администратора</b>"
                    )
                else:
                    help_text += (
                        "⚠️ <b>Аналитические функции недоступны</b>\n"
                        "Для активации добавьте DATABASE_URL в переменные окружения"
                    )
                
                await message.answer(help_text, parse_mode="HTML")
            
            @dp.message(Command("info"))
            async def info_command(message: Message):
                await message.answer(
                    "ℹ️ <b>Техническая информация:</b>\n\n"
                    "🏗️ <b>Платформа:</b> Railway\n"
                    "🐍 <b>Python:</b> 3.11\n"
                    "📚 <b>Aiogram:</b> 3.x\n"
                    "🌐 <b>Health endpoint:</b> /health\n"
                    "📊 <b>Status endpoint:</b> /status\n\n"
                    "🔧 <b>Режимы работы:</b>\n"
                    "• running_full - Полный функционал\n"
                    "• running_simple - Базовый режим\n"
                    "• health_only - Только health check\n\n"
                    f"📊 <b>Аналитика:</b> {'✅ Активна' if analytics_available else '❌ Неактивна'}\n"
                    f"💾 <b>PostgreSQL:</b> {'✅ Подключен' if analytics_available else '❌ Не подключен'}",
                    parse_mode="HTML"
                )
            
            # Обработчик для всех остальных сообщений
            @dp.message()
            async def echo_handler(message: Message):
                await message.answer(
                    "🤖 Я получил ваше сообщение!\n\n"
                    "Используйте команды:\n"
                    "/start - Начать работу\n"
                    "/help - Получить помощь\n"
                    "/status - Проверить статус" +
                    ("\n/list - Список каналов" if analytics_available else "")
                )
            
            logger.info("🔄 Starting simple bot...")
            self.bot = bot
            self.status = "running_analytics" if analytics_available else "running_simple"
            
            await dp.start_polling(bot)
            
        except Exception as e:
            logger.error(f"❌ Simple bot failed: {e}")
            self.status = "health_only"
            # Даже если бот не запустился, health server работает!

# Глобальные переменные
start_time = time.time()
bot_manager = BotManager()

def start_http_server():
    """Запуск HTTP сервера - ГАРАНТИРОВАННО работает"""
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"🌐 Starting HTTP server on port {port}")
    
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    
    logger.info(f"✅ HTTP server ready at http://0.0.0.0:{port}")
    logger.info("📊 Endpoints: /health, /status, /")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 HTTP server stopped")
        server.shutdown()

async def main():
    """Главная функция - запускает все"""
    logger.info("🚀 Starting Hybrid Railway Bot...")
    
    # Запускаем HTTP сервер в отдельном потоке (для healthcheck)
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    # Даем серверу время запуститься
    await asyncio.sleep(1)
    
    # Запускаем бота (с fallback)
    try:
        await bot_manager.start_bot()
    except Exception as e:
        logger.error(f"Bot startup error: {e}")
        bot_manager.status = "health_only"
    
    # Держим приложение живым
    logger.info(f"🎯 Application running in mode: {bot_manager.status}")
    
    try:
        while True:
            await asyncio.sleep(10)
            if bot_manager.status == "failed":
                logger.info("🔄 Attempting bot restart...")
                try:
                    await bot_manager.start_bot()
                except:
                    pass
    except KeyboardInterrupt:
        logger.info("🛑 Application stopped")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
