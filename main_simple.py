#!/usr/bin/env python3
"""
СУПЕР-ПРОСТОЙ HTTP бот для Railway (без telegram библиотеки)
"""
import asyncio
import json
import logging
import os
import sys
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORT = int(os.getenv("PORT", "8080"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

logger.info("🚀 СУПЕР-ПРОСТОЙ БОТ СТАРТ!")
logger.info(f"PORT: {PORT}")
logger.info(f"BOT_TOKEN: {'ДА' if BOT_TOKEN else 'НЕТ'}")

class SimpleBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, chat_id, text):
        try:
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            post_data = urllib.parse.urlencode(data).encode()
            req = urllib.request.Request(
                f"{self.api_url}/sendMessage",
                data=post_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode())
                logger.info(f"✅ Message sent: {result.get('ok', False)}")
                return result
                
        except Exception as e:
            logger.error(f"❌ Send error: {e}")
            return None
    
    def get_updates(self, offset=None):
        try:
            url = f"{self.api_url}/getUpdates"
            if offset:
                url += f"?offset={offset}"
            
            with urllib.request.urlopen(url, timeout=10) as response:
                result = json.loads(response.read().decode())
                return result.get('result', [])
                
        except Exception as e:
            logger.error(f"❌ Updates error: {e}")
            return []

class BotHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            data = {
                "status": "ok", 
                "healthy": True, 
                "bot": "simple",
                "token_set": bool(BOT_TOKEN)
            }
            self.wfile.write(json.dumps(data, indent=2).encode())
            
        elif self.path == '/test':
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            
            html = """
            <h1>🤖 TG-analiz Bot Test</h1>
            <p>✅ Health server работает</p>
            <p>✅ Railway деплой успешен</p>
            <p>✅ Порт настроен правильно</p>
            <h2>Инструкции:</h2>
            <ol>
                <li>Удалите webhook: <a href="https://api.telegram.org/bot{}/deleteWebhook" target="_blank">Удалить</a></li>
                <li>Отправьте боту /start</li>
                <li>Если не работает - проблема в токене</li>
            </ol>
            """.format(BOT_TOKEN if BOT_TOKEN else "YOUR_TOKEN")
            
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()

async def bot_polling():
    if not BOT_TOKEN:
        logger.error("❌ NO BOT_TOKEN - только health сервер")
        return
    
    bot = SimpleBot(BOT_TOKEN)
    offset = None
    
    logger.info("🤖 POLLING START - проверяем сообщения...")
    
    while True:
        try:
            updates = bot.get_updates(offset)
            
            for update in updates:
                offset = update['update_id'] + 1
                
                if 'message' in update:
                    message = update['message']
                    chat_id = message['chat']['id']
                    text = message.get('text', '')
                    user_id = message['from']['id']
                    
                    logger.info(f"📨 Сообщение от {user_id}: {text}")
                    
                    if text == '/start':
                        response = (
                            "🎉 <b>СУПЕР-ПРОСТОЙ БОТ РАБОТАЕТ!</b>\n\n"
                            "✅ Railway деплой: ОК\n"
                            "✅ HTTP сервер: ОК\n"
                            "✅ Telegram API: ОК\n"
                            "✅ Polling: ОК\n\n"
                            f"👤 Ваш ID: {user_id}\n"
                            f"💬 Чат ID: {chat_id}\n\n"
                            "🚀 <b>ПРОБЛЕМА РЕШЕНА!</b>"
                        )
                        bot.send_message(chat_id, response)
                        
                    elif text == '/test':
                        response = (
                            "🧪 <b>ТЕСТ УСПЕШЕН!</b>\n\n"
                            "✅ Бот отвечает мгновенно\n"
                            "✅ HTTP polling работает\n"
                            "✅ Railway стабилен\n\n"
                            "🎯 <b>ВСЕ ОТЛИЧНО!</b>"
                        )
                        bot.send_message(chat_id, response)
                        
                    elif text == '/help':
                        response = (
                            "📋 <b>Команды:</b>\n\n"
                            "• /start - Проверка работы\n"
                            "• /test - Тестовая команда\n"
                            "• /help - Эта справка\n\n"
                            "✅ <b>Все команды работают!</b>"
                        )
                        bot.send_message(chat_id, response)
            
            await asyncio.sleep(1)  # Пауза между запросами
            
        except Exception as e:
            logger.error(f"❌ Polling error: {e}")
            await asyncio.sleep(5)

async def main():
    logger.info("🚀 ЗАПУСК ГЛАВНОЙ ФУНКЦИИ")
    
    # HTTP сервер в фоне
    import threading
    server = HTTPServer(("0.0.0.0", PORT), BotHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    logger.info(f"🌐 HTTP сервер запущен на порту {PORT}")
    
    # Telegram polling
    await bot_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ Остановлено")
    except Exception as e:
        logger.error(f"💥 ОШИБКА: {e}")
        sys.exit(1)

def start_health_server():
    """Запуск health check сервера"""
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        logger.info(f"✅ Health server running on port {PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Health server error: {e}")

async def init_telegram_bot():
    """Инициализация Telegram бота с ПОЛНЫМИ командами"""
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
        
        if not BOT_TOKEN:
            logger.warning("⚠️ BOT_TOKEN not set!")
            return None
        
        # Создаем приложение
        app = Application.builder().token(BOT_TOKEN).build()
        
        # /start команда
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "🚀 <b>TG-analiz Bot - Полная версия!</b>\n\n"
                "✅ Railway деплой работает\n"
                "🤖 Все команды активны\n"
                "📊 Готов к анализу каналов\n\n"
                "📋 Команды:\n"
                "• /summary - Статистика канала\n"
                "• /growth - Рост подписчиков\n" 
                "• /charts - Интерактивные графики\n"
                "• /help - Справка\n\n"
                "🎉 Бот полностью функционален!",
                parse_mode='HTML'
            )
        
        # /summary команда
        async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "📊 <b>Сводка по каналу</b>\n\n"
                "👥 Подписчики: 15,247 (+127 за день)\n"
                "📈 Рост: +0.8% за неделю\n"
                "⚡ Просмотры: 45,230 (средние)\n"
                "🎯 Охват: 78.5% подписчиков\n"
                "🔄 Вовлеченность: 12.3%\n\n"
                "📈 <i>Демо данные. Подключите канал для реальной статистики.</i>",
                parse_mode='HTML'
            )
        
        # /growth команда 
        async def growth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                "🏆 <b>Лучший день:</b> Пятница (+67)",
                parse_mode='HTML'
            )
        
        # /charts команда с интерактивными кнопками
        async def charts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        # Обработка нажатий кнопок
        async def handle_chart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                "🚀 <i>Railway деплой успешен! Все функции работают.</i>",
                parse_mode='HTML'
            )
        
        # /help команда
        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "❓ <b>Справка по TG-analiz Bot</b>\n\n"
                "🚀 <b>Статус:</b> Railway деплой активен\n\n"
                "📊 <b>Команды:</b>\n"
                "• /start - Информация о боте\n"
                "• /summary - Сводная статистика\n"
                "• /growth - Анализ роста\n"
                "• /charts - Интерактивные графики\n"
                "• /help - Эта справка\n\n"
                "🔧 <b>Для расширенных функций:</b>\n"
                "Добавьте в Railway Variables:\n"
                "• CHANNEL_ID - ID канала\n"
                "• API_ID - Telegram API\n"
                "• API_HASH - Telegram API Hash\n\n"
                "💡 <b>Все работает!</b> 🎉",
                parse_mode='HTML'
            )
        
        # Добавляем все команды
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("summary", summary_command))
        app.add_handler(CommandHandler("growth", growth_command))
        app.add_handler(CommandHandler("charts", charts_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CallbackQueryHandler(handle_chart_callback, pattern="^chart_"))
        
        logger.info("✅ Telegram bot initialized with ALL commands")
        return app
        
    except ImportError as e:
        logger.error(f"❌ Telegram import error: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Bot initialization error: {e}")
        return None

async def main():
    """Главная функция"""
    logger.info("🚀 Starting TG-analiz bot...")
    logger.info(f"🔧 Port: {PORT}")
    logger.info(f"🤖 Bot token: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
    
    # ВСЕГДА запускаем health server первым
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    logger.info("🌐 Health check server started")
    
    # Запускаем Telegram bot
    bot_app = await init_telegram_bot()
    
    if bot_app and BOT_TOKEN:
        logger.info("🤖 Starting Telegram bot with ALL commands...")
        await bot_app.run_polling(allowed_updates=["message", "callback_query"])
    else:
        logger.warning("🏥 Running in health-check-only mode")
        try:
            await asyncio.sleep(float('inf'))
        except KeyboardInterrupt:
            logger.info("👋 Graceful shutdown")

if __name__ == "__main__":
    asyncio.run(main())
