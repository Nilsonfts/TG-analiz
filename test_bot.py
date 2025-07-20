#!/usr/bin/env python3
"""
Простой Telegram бот для тестирования - без базы данных
"""
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🚀 <b>Telegram Channel Analytics Bot</b>\n\n"
        "✅ Бот запущен и готов к работе!\n"
        "💡 Введите ваш токен в .env файл\n\n"
        "📊 Доступные команды:\n"
        "• /summary - Статистика канала\n"
        "• /growth - Рост подписчиков\n"
        "• /charts - Графики\n"
        "• /help - Помощь",
        parse_mode='HTML'
    )

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /summary"""
    await update.message.reply_text(
        "📊 <b>Сводка по каналу</b>\n\n"
        "👥 Подписчики: 15,247 (+127 за день)\n"
        "📈 Рост: +0.8% за неделю\n"
        "⚡ Просмотры: 45,230 (средние)\n"
        "🎯 Охват: 78.5% подписчиков\n\n"
        "🤖 <i>Это тестовые данные. Настройте реальный канал в коде.</i>",
        parse_mode='HTML'
    )

async def growth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /growth"""
    await update.message.reply_text(
        "📈 <b>Рост подписчиков</b>\n\n"
        "📅 <b>За 7 дней:</b>\n"
        "• Понедельник: +45\n"
        "• Вторник: +38\n"
        "• Среда: +52\n"
        "• Четверг: +41\n"
        "• Пятница: +67\n"
        "• Суббота: +34\n"
        "• Воскресенье: +28\n\n"
        "📊 Итого: +305 подписчиков\n"
        "💡 Лучший день: Пятница (+67)",
        parse_mode='HTML'
    )

async def charts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /charts"""
    keyboard = [
        [InlineKeyboardButton("📈 Рост подписчиков", callback_data="chart_growth")],
        [InlineKeyboardButton("⏰ Активность по часам", callback_data="chart_activity")],
        [InlineKeyboardButton("🎯 Источники трафика", callback_data="chart_traffic")],
        [InlineKeyboardButton("📊 Дашборд", callback_data="chart_dashboard")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📊 <b>Выберите тип графика:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_chart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок графиков"""
    query = update.callback_query
    await query.answer()
    
    chart_type = query.data.replace("chart_", "")
    
    messages = {
        "growth": "📈 Генерируем график роста подписчиков...",
        "activity": "⏰ Строим график активности по часам...",
        "traffic": "🎯 Создаем диаграммы источников трафика...",
        "dashboard": "🎛 Собираем полный дашборд..."
    }
    
    await query.edit_message_text(
        f"{messages.get(chart_type, '📊 Генерируем график...')}\n\n"
        "🤖 <i>Графики будут готовы после настройки полной системы аналитики.</i>",
        parse_mode='HTML'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "❓ <b>Справка по боту</b>\n\n"
        "📊 <b>Основные команды:</b>\n"
        "• /start - Запуск бота\n"
        "• /summary - Сводная статистика\n"
        "• /growth - Рост подписчиков\n"
        "• /charts - Интерактивные графики\n"
        "• /help - Эта справка\n\n"
        "🔧 <b>Настройка:</b>\n"
        "1. Добавьте BOT_TOKEN в .env файл\n"
        "2. Настройте подключение к каналу\n"
        "3. Инициализируйте базу данных\n\n"
        "💡 <b>Полная документация:</b> SETUP.md",
        parse_mode='HTML'
    )

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка неизвестных команд"""
    await update.message.reply_text(
        "❓ Неизвестная команда.\n\n"
        "Введите /help для списка доступных команд."
    )

def main():
    """Основная функция"""
    if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
        print("❌ Ошибка: BOT_TOKEN не настроен!")
        print("💡 Добавьте ваш токен бота в файл .env")
        print("   BOT_TOKEN=ваш_токен_от_BotFather")
        return
    
    print("🚀 Запуск Telegram Channel Analytics Bot...")
    print(f"🤖 Токен: {BOT_TOKEN[:10]}...")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("growth", growth_command))
    application.add_handler(CommandHandler("charts", charts_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик нажатий кнопок
    application.add_handler(CallbackQueryHandler(handle_chart_callback, pattern="^chart_"))
    
    # Обработчик неизвестных команд (должен быть последним)
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    print("✅ Бот запущен! Нажмите Ctrl+C для остановки.")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
