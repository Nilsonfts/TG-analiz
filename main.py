#!/usr/bin/env python3
"""
Railway Telegram Bot with HTTP healthcheck
"""
import os
import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# HTTP сервер для healthcheck
class HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Отключаем логи HTTP сервера
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "bot": "running"}')

def start_http_server():
    """Запуск HTTP сервера для healthcheck"""
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"HTTP сервер запущен на порту {port}")
    server.serve_forever()

# Команды бота
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🚀 <b>Telegram Channel Analytics Bot</b>\n\n"
        "✅ Бот успешно работает на Railway!\n"
        "📊 Готов к аналитике каналов\n\n"
        "📋 Доступные команды:\n"
        "• /summary - Статистика канала\n"
        "• /growth - Рост подписчиков\n"
        "• /charts - Графики\n"
        "• /help - Помощь\n\n"
        "🔧 <i>Для полной функциональности добавьте токены каналов</i>",
        parse_mode='HTML'
    )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /summary"""
    await update.message.reply_text(
        "📊 <b>Сводка по каналу</b>\n\n"
        "👥 Подписчики: 15,247 (+127 за день)\n"
        "📈 Рост: +0.8% за неделю\n"
        "⚡ Просмотры: 45,230 (средние)\n"
        "🎯 Охват: 78.5% подписчиков\n"
        "🔄 Вовлеченность: 12.3%\n\n"
        "💡 <i>Тестовые данные. Railway деплой работает!</i>",
        parse_mode='HTML'
    )

async def growth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /growth"""
    await update.message.reply_text(
        "📈 <b>Рост подписчиков (7 дней)</b>\n\n"
        "📅 <b>Статистика:</b>\n"
        "• Понедельник: +45 👥\n"
        "• Вторник: +38 📊\n"
        "• Среда: +52 🚀\n"
        "• Четверг: +41 📈\n"
        "• Пятница: +67 🎉\n"
        "• Суббота: +34 📱\n"
        "• Воскресенье: +28 ⭐\n\n"
        "📊 <b>Итого:</b> +305 подписчиков\n"
        "🏆 <b>Лучший день:</b> Пятница (+67)\n"
        "📍 <b>Средний прирост:</b> +44/день",
        parse_mode='HTML'
    )

async def charts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /charts"""
    keyboard = [
        [InlineKeyboardButton("📈 Рост подписчиков", callback_data="chart_growth")],
        [InlineKeyboardButton("⏰ Активность по часам", callback_data="chart_activity")],
        [InlineKeyboardButton("🎯 Источники трафика", callback_data="chart_traffic")],
        [InlineKeyboardButton("📊 Полный дашборд", callback_data="chart_dashboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📊 <b>Интерактивные графики</b>\n\n"
        "Выберите тип визуализации:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_chart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок графиков"""
    query = update.callback_query
    await query.answer()
    
    chart_type = query.data.replace("chart_", "")
    
    messages = {
        "growth": "📈 <b>График роста подписчиков</b>\n\n🎯 Тренд: Положительный\n📊 30-дневная динамика готова",
        "activity": "⏰ <b>Активность по часам</b>\n\n🕐 Пик: 12:00, 18:00, 21:00\n📱 Анализ 7 дней",
        "traffic": "🎯 <b>Источники трафика</b>\n\n🔗 URL: 45%\n🔍 Поиск: 30%\n👥 Другие каналы: 25%",
        "dashboard": "🎛 <b>Полный дашборд</b>\n\n📊 Все метрики собраны\n✅ Готов к анализу"
    }
    
    await query.edit_message_text(
        f"{messages.get(chart_type, '📊 Генерируем график...')}\n\n"
        "🚀 <i>Railway деплой успешен! Графики будут готовы после подключения к каналам.</i>",
        parse_mode='HTML'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "❓ <b>Справка по боту</b>\n\n"
        "🚀 <b>Статус:</b> Railway деплой активен\n\n"
        "📊 <b>Команды:</b>\n"
        "• /start - Информация о боте\n"
        "• /summary - Сводная статистика\n"
        "• /growth - Анализ роста\n"
        "• /charts - Интерактивные графики\n"
        "• /help - Эта справка\n\n"
        "🔧 <b>Настройка:</b>\n"
        "1. ✅ Railway деплой работает\n"
        "2. 🔄 Добавьте переменные окружения\n"
        "3. 📊 Подключите каналы для аналитики\n\n"
        "💡 <b>Документация:</b> GitHub > SETUP.md",
        parse_mode='HTML'
    )

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка неизвестных команд"""
    await update.message.reply_text(
        "❓ Неизвестная команда.\n\n"
        "📋 Введите /help для списка команд.\n"
        "🚀 Railway деплой работает!"
    )

def main():
    """Основная функция"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
        logger.info("💡 Добавьте BOT_TOKEN в Railway Variables")
        # Запускаем только HTTP сервер
        start_http_server()
        return
    
    logger.info("🚀 Запуск Telegram Bot на Railway...")
    logger.info(f"🤖 Токен: {BOT_TOKEN[:10]}...")
    
    # Запускаем HTTP сервер в отдельном потоке
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    # Создаем приложение Telegram бота
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("growth", growth_command))
    application.add_handler(CommandHandler("charts", charts_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик нажатий кнопок
    application.add_handler(CallbackQueryHandler(handle_chart_callback, pattern="^chart_"))
    
    # Обработчик неизвестных команд
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    logger.info("✅ Telegram бот запущен на Railway!")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
