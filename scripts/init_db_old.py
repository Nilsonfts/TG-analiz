#!/usr/bin/env python3
"""
Initialize database and create first Alembic migration.
"""
import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from src.config import settings
from src.db.models import DatabaseManager
from src.utils.logging import get_logger

logger = get_logger("init_db")


async def init_database():
    """Initialize database and create tables."""
    logger.info("�️ Initializing database...")
    
    try:
        # Create database manager
        db_manager = DatabaseManager(settings.database_url)
        
        # Create all tables
        await db_manager.create_tables()
        
        logger.info("✅ Database tables created successfully")
        
        # Close connections
        await db_manager.close()
        
        return True
        
    except Exception as e:
        logger.error("❌ Failed to initialize database", error=str(e))
        return False

def create_alembic_migration():
    """Create initial Alembic migration."""
    logger.info("📝 Creating Alembic migration...")
    
    try:
        import subprocess
        
        # Create initial migration
        result = subprocess.run([
            "alembic", "revision", "--autogenerate", 
            "-m", "Initial migration with all tables"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Alembic migration created successfully")
            return True
        else:
            logger.error("❌ Failed to create migration", stderr=result.stderr)
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error("❌ Alembic command failed", error=str(e))
        return False
    except FileNotFoundError:
        logger.error("❌ Alembic not found - install with: pip install alembic")
        return False


async def main():
    """Main initialization function."""
    logger.info("🚀 Database initialization started...")
    
    # Check if database URL is configured
    if not settings.database_url:
        logger.error("❌ DATABASE_URL not configured")
        return 1
    
    # Initialize database
    if not await init_database():
        return 1
    
    # Create Alembic migration
    if not create_alembic_migration():
        logger.warning("⚠️ Migration creation failed - you may need to run manually")
    
    logger.info("✅ Database initialization completed")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
        'API_HASH',
        'DATABASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Отсутствуют обязательные переменные окружения:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Создайте файл .env на основе .env.example и заполните все переменные")
        return False
    
    print("✅ Все переменные окружения настроены")
    return True

async def main():
    """Главная функция инициализации"""
    print("🚀 Запуск инициализации Telegram Analytics Bot")
    print("=" * 50)
    
    # Проверка переменных окружения
    if not check_environment():
        return
    
    # Инициализация базы данных
    await init_database()
    
    # Добавление примеров групп
    add_sample_groups()
    
    print("\n" + "=" * 50)
    print("🎉 Инициализация завершена!")
    print("\n📋 Следующие шаги:")
    print("1. Обновите ID групп в базе данных на реальные")
    print("2. Добавьте бот в группы, которые хотите мониторить")
    print("3. Запустите бот командой: python main.py")
    print("\n💡 Используйте команду /start в боте для начала работы")

if __name__ == "__main__":
    asyncio.run(main())
