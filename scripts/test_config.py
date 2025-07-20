#!/usr/bin/env python3
"""
Скрипт для тестирования настроек бота перед запуском
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.health import health_checker

load_dotenv()


def check_files():
    """Проверка наличия необходимых файлов"""
    required_files = [
        "main.py",
        "requirements.txt",
        ".env",
        "database/models.py",
        "services/analytics_service.py",
        "services/report_service.py",
        "services/scheduler_service.py",
        "handlers/commands.py",
        "utils/auth.py",
    ]

    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print("❌ Отсутствуют файлы:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False

    print("✅ Все необходимые файлы присутствуют")
    return True


def check_directories():
    """Проверка наличия необходимых директорий"""
    required_dirs = [
        "database",
        "services",
        "handlers",
        "utils",
        "scripts",
        "charts",
        "reports",
    ]

    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"📁 Создана директория: {dir_path}")

    print("✅ Все директории готовы")
    return True


async def test_bot_configuration():
    """Тестирование конфигурации бота"""
    print("🔄 Тестирование конфигурации бота...")

    try:
        health_status = await health_checker.perform_health_check()

        print(f"📊 Статус проверки: {health_status['status']}")

        for check_name, result in health_status["checks"].items():
            status_emoji = "✅" if result else "❌"
            print(f"   {status_emoji} {check_name}: {'OK' if result else 'FAILED'}")

        if health_status["errors"]:
            print("\n❌ Ошибки:")
            for error in health_status["errors"]:
                print(f"   - {error}")

        return health_status["status"] == "healthy"

    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False


def show_configuration():
    """Показать текущую конфигурацию"""
    print("\n📋 Текущая конфигурация:")

    config_vars = [
        ("BOT_TOKEN", "скрыт" if os.getenv("BOT_TOKEN") else "не установлен"),
        ("API_ID", os.getenv("API_ID", "не установлен")),
        ("API_HASH", "скрыт" if os.getenv("API_HASH") else "не установлен"),
        (
            "DATABASE_URL",
            "установлен" if os.getenv("DATABASE_URL") else "не установлен",
        ),
        ("ADMIN_USERS", os.getenv("ADMIN_USERS", "не установлен")),
        ("TIMEZONE", os.getenv("TIMEZONE", "Europe/Moscow")),
        ("PORT", os.getenv("PORT", "8000")),
    ]

    for var_name, var_value in config_vars:
        print(f"   {var_name}: {var_value}")


def show_next_steps():
    """Показать следующие шаги"""
    print("\n🚀 Следующие шаги:")
    print("1. Убедитесь, что все переменные окружения настроены в .env")
    print("2. Запустите инициализацию: python scripts/init_db.py")
    print(
        "3. Добавьте группы для мониторинга: python scripts/manage_groups.py add @username"
    )
    print("4. Запустите бота: python main.py")
    print("\n📝 Для Railway:")
    print("1. Убедитесь, что все переменные настроены в Railway dashboard")
    print("2. Развертывание произойдет автоматически после push в git")


async def main():
    """Главная функция"""
    print("🤖 Тестирование Telegram Analytics Bot")
    print("=" * 50)

    # Проверка файлов
    if not check_files():
        print("\n❌ Исправьте отсутствующие файлы и запустите тест снова")
        return

    # Проверка директорий
    check_directories()

    # Показ конфигурации
    show_configuration()

    # Тестирование конфигурации
    is_healthy = await test_bot_configuration()

    print("\n" + "=" * 50)

    if is_healthy:
        print("🎉 Бот готов к запуску!")
        show_next_steps()
    else:
        print("❌ Обнаружены проблемы. Исправьте их перед запуском.")
        print("\n💡 Наиболее частые проблемы:")
        print("- Неправильные токены Telegram")
        print("- Недоступность базы данных")
        print("- Отсутствующие переменные окружения")


if __name__ == "__main__":
    asyncio.run(main())
