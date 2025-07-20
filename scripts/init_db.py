#!/usr/bin/env python3
"""
Скрипт инициализации базы данных и добавления групп для мониторинга
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import init_db, get_db, TelegramGroup

load_dotenv()

async def init_database():
    """Инициализация базы данных"""
    print("🔄 Инициализация базы данных...")
    await init_db()
    print("✅ База данных инициализирована")

def add_sample_groups():
    """Добавление примеров групп для мониторинга"""
    db = get_db()
    try:
        # Проверяем, есть ли уже группы
        existing_groups = db.query(TelegramGroup).count()
        if existing_groups > 0:
            print(f"📊 В базе уже есть {existing_groups} групп")
            return

        sample_groups = [
            {
                'group_id': -1001234567890,  # Замените на реальные ID групп
                'username': 'example_group1',
                'title': 'Пример группы 1',
                'description': 'Описание первой группы для мониторинга',
                'members_count': 1500
            },
            {
                'group_id': -1001234567891,  # Замените на реальные ID групп
                'username': 'example_group2',
                'title': 'Пример группы 2',
                'description': 'Описание второй группы для мониторинга',
                'members_count': 850
            }
        ]

        for group_data in sample_groups:
            group = TelegramGroup(**group_data)
            db.add(group)

        db.commit()
        print(f"✅ Добавлено {len(sample_groups)} примеров групп")
        print("⚠️  Не забудьте изменить ID групп на реальные в файле init_db.py")

    except Exception as e:
        print(f"❌ Ошибка при добавлении групп: {e}")
        db.rollback()
    finally:
        db.close()

def check_environment():
    """Проверка переменных окружения"""
    required_vars = [
        'BOT_TOKEN',
        'API_ID',
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
