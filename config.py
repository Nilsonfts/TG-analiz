import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Конфигурация приложения"""
    
    def __init__(self):
        # Telegram Bot
        self.bot_token = os.getenv('BOT_TOKEN')
        if not self.bot_token:
            print("⚠️  BOT_TOKEN не найден в переменных окружения!")
            print("💡 Установите переменную BOT_TOKEN для работы Telegram бота")
        
        # Telegram API (опционально для начала)
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        
        # База данных (опционально для начала)
        # Используем DATABASE_PUBLIC_URL для внешнего подключения, или DATABASE_URL для внутреннего
        self.database_url = os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL', 'postgresql://localhost/tg_analytics')
        
        # Railway фикс: заменяем postgres:// на postgresql://
        if self.database_url and self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        
        # Администраторы
        admin_users_str = os.getenv('ADMIN_USERS', '')
        self.admin_users = [int(x.strip()) for x in admin_users_str.split(',') if x.strip().isdigit()]
        
        # Дополнительные настройки
        self.timezone = os.getenv('TIMEZONE', 'UTC')
        self.reports_chat_id = os.getenv('REPORTS_CHAT_ID')
        self.port = int(os.getenv('PORT', 8000))
        
        # Настройки сбора данных
        self.collection_interval = int(os.getenv('COLLECTION_INTERVAL', 3600))  # 1 час
        self.max_messages_per_request = int(os.getenv('MAX_MESSAGES_PER_REQUEST', 100))
        
        # Безопасность
        self.session_string = os.getenv('SESSION_STRING', 'bot_session')
        
        print(f"📋 Конфигурация загружена:")
        print(f"   BOT_TOKEN: {'✅ Установлен' if self.bot_token else '❌ Не найден'}")
        print(f"   ADMIN_USERS: {len(self.admin_users)} администраторов")
