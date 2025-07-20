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
            raise ValueError("BOT_TOKEN не найден в переменных окружения")
        
        # Telegram API
        self.api_id = os.getenv('API_ID')
        self.api_hash = os.getenv('API_HASH')
        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID или API_HASH не найдены в переменных окружения")
        
        # База данных
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL не найден в переменных окружения")
        
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
