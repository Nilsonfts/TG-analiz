#!/usr/bin/env python3
"""
Тестовый скрипт для проверки всех компонентов бота
"""
import sys
import os

def test_imports():
    """Тестируем импорты всех ключевых модулей"""
    print("🔍 Проверяем импорты...")
    
    try:
        import aiogram
        print("✅ aiogram")
    except ImportError as e:
        print(f"❌ aiogram: {e}")
        return False
    
    try:
        import telegram
        print("✅ python-telegram-bot")
    except ImportError as e:
        print(f"❌ python-telegram-bot: {e}")
        return False
    
    try:
        import apscheduler
        print("✅ apscheduler")
    except ImportError as e:
        print(f"❌ apscheduler: {e}")
        return False
    
    try:
        import telethon
        print("✅ telethon")
    except ImportError as e:
        print(f"❌ telethon: {e}")
        return False
    
    try:
        import sqlalchemy
        print("✅ sqlalchemy")
    except ImportError as e:
        print(f"❌ sqlalchemy: {e}")
        return False
    
    try:
        import matplotlib
        print("✅ matplotlib")
    except ImportError as e:
        print(f"❌ matplotlib: {e}")
        return False
    
    return True

def test_env_variables():
    """Проверяем переменные окружения"""
    print("\n🔧 Проверяем переменные окружения...")
    
    required_vars = [
        'BOT_TOKEN',
        'API_ID', 
        'API_HASH',
        'CHANNEL_ID',
        'ADMIN_USERS'
    ]
    
    missing_vars = []
    
    # Пытаемся загрузить .env файл
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env файл загружен")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки .env: {e}")
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == "**ACTION_REQUIRED**":
            print(f"❌ {var}: не настроена")
            missing_vars.append(var)
        else:
            # Скрываем токены для безопасности
            if 'TOKEN' in var or 'HASH' in var:
                print(f"✅ {var}: настроена (***)")
            else:
                print(f"✅ {var}: {value}")
    
    return len(missing_vars) == 0, missing_vars

def test_file_structure():
    """Проверяем структуру файлов"""
    print("\n📁 Проверяем структуру файлов...")
    
    required_files = [
        'main.py',
        'requirements.txt', 
        'Dockerfile',
        'Procfile',
        '.env'
    ]
    
    missing_files = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            missing_files.append(file)
    
    return len(missing_files) == 0, missing_files

def main():
    print("🚀 ТЕСТ КОМПОНЕНТОВ TG-ANALIZ БОТА\n")
    
    # Тест импортов
    imports_ok = test_imports()
    
    # Тест переменных окружения
    env_ok, missing_vars = test_env_variables()
    
    # Тест структуры файлов
    files_ok, missing_files = test_file_structure()
    
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("="*50)
    
    if imports_ok:
        print("✅ Все модули импортируются")
    else:
        print("❌ Проблемы с импортами - проверьте requirements.txt")
    
    if files_ok:
        print("✅ Все файлы на месте")
    else:
        print(f"❌ Отсутствуют файлы: {', '.join(missing_files)}")
    
    if env_ok:
        print("✅ Все переменные окружения настроены")
    else:
        print(f"❌ Не настроены: {', '.join(missing_vars)}")
        print("\n💡 Для исправления:")
        print("1. Получите токен у @BotFather")
        print("2. Получите API данные на https://my.telegram.org")
        print("3. Обновите файл .env")
    
    print("\n" + "="*50)
    
    if imports_ok and files_ok and env_ok:
        print("🎉 ВСЕ ГОТОВО! Бот готов к запуску!")
        return 0
    else:
        print("⚠️ ТРЕБУЮТСЯ ИСПРАВЛЕНИЯ перед запуском")
        return 1

if __name__ == "__main__":
    sys.exit(main())
