"""
Configuration management for Channel Analytics bot.
"""
import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Telegram Bot Configuration
    bot_token: str = Field(default="", description="Telegram bot token from @BotFather")
    telegram_api_id: int = Field(default=0, description="Telegram API ID from my.telegram.org")
    telegram_api_hash: str = Field(default="", description="Telegram API hash from my.telegram.org")
    
    # Admin Configuration
    admin_user_ids: List[int] = Field(default_factory=list, description="List of admin user IDs")
    report_chat_id: Optional[int] = Field(None, description="Chat ID for automated reports")
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://localhost/channel_analytics",
        description="PostgreSQL database URL"
    )
    
    # External API Configuration
    telemetr_api_key: Optional[str] = Field(None, description="Telemetr.me API key")
    tgstat_api_key: Optional[str] = Field(None, description="TGStat.ru API key")
    
    # Scheduler Configuration
    daily_job_hour: int = Field(default=2, description="Hour for daily data collection (UTC)")
    weekly_job_hour: int = Field(default=4, description="Hour for weekly reports (UTC)")
    monthly_job_hour: int = Field(default=5, description="Hour for monthly reports (UTC)")
    
    # Rate Limiting
    telegram_api_limit: int = Field(default=60, description="Telegram API requests per minute")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    sentry_dsn: Optional[str] = Field(None, description="Sentry DSN for error tracking")
    
    # Performance Configuration
    max_memory_mb: int = Field(default=512, description="Maximum memory usage in MB")
    request_timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    
    # Development Configuration
    debug: bool = Field(default=False, description="Enable debug mode")
    testing: bool = Field(default=False, description="Enable testing mode")
    
    # Railway Configuration
    port: int = Field(default=int(os.getenv("PORT", "8080")), description="HTTP server port")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Environment variable mappings
        fields = {
            "bot_token": {"env": "BOT_TOKEN"},
            "telegram_api_id": {"env": ["TELEGRAM_API_ID", "API_ID"]},
            "telegram_api_hash": {"env": ["TELEGRAM_API_HASH", "API_HASH"]},
            "admin_user_ids": {"env": "ADMIN_USER_IDS"},
            "report_chat_id": {"env": "REPORT_CHAT_ID"},
            "database_url": {"env": "DATABASE_URL"},
            "telemetr_api_key": {"env": "TELEMETR_API_KEY"},
            "tgstat_api_key": {"env": "TGSTAT_API_KEY"},
            "sentry_dsn": {"env": "SENTRY_DSN"},
        }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Handle alternative environment variable names
        # API_ID -> TELEGRAM_API_ID
        if not self.telegram_api_id and os.getenv("API_ID"):
            self.telegram_api_id = int(os.getenv("API_ID"))
        
        # API_HASH -> TELEGRAM_API_HASH  
        if not self.telegram_api_hash and os.getenv("API_HASH"):
            self.telegram_api_hash = os.getenv("API_HASH")
            
        # ADMIN_USERS -> ADMIN_USER_IDS
        admin_users_str = os.getenv("ADMIN_USER_IDS", "") or os.getenv("ADMIN_USERS", "")
        if admin_users_str:
            self.admin_user_ids = [
                int(uid.strip()) for uid in admin_users_str.split(",") 
                if uid.strip().isdigit()
            ]
            
        # REPORTS_CHAT_ID -> REPORT_CHAT_ID
        if not self.report_chat_id and os.getenv("REPORTS_CHAT_ID"):
            self.report_chat_id = int(os.getenv("REPORTS_CHAT_ID"))


# Global settings instance
settings = Settings()
