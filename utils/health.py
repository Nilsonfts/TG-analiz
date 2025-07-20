import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthCheck:
    """Класс для проверки здоровья приложения"""

    def __init__(self):
        self.last_check = None
        self.status = "starting"
        self.errors = []

    async def check_database(self) -> bool:
        """Проверка подключения к базе данных"""
        try:
            from database.models import get_db

            db = get_db()
            try:
                # Простой запрос для проверки соединения
                db.execute("SELECT 1")
                return True
            finally:
                db.close()
        except Exception as e:
            self.errors.append(f"Database error: {e}")
            return False

    async def check_telegram_connection(self) -> bool:
        """Проверка подключения к Telegram API"""
        try:
            from telethon import TelegramClient

            api_id = int(os.getenv("API_ID"))
            api_hash = os.getenv("API_HASH")

            client = TelegramClient("health_check_session", api_id, api_hash)

            try:
                await client.start()
                # Простая проверка - получение информации о себе
                me = await client.get_me()
                return me is not None
            finally:
                await client.disconnect()

        except Exception as e:
            self.errors.append(f"Telegram API error: {e}")
            return False

    async def check_environment(self) -> bool:
        """Проверка переменных окружения"""
        required_vars = ["BOT_TOKEN", "API_ID", "API_HASH", "DATABASE_URL"]

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self.errors.append(
                f"Missing environment variables: {', '.join(missing_vars)}"
            )
            return False

        return True

    async def perform_health_check(self) -> dict:
        """Выполнение полной проверки здоровья"""
        self.errors = []
        self.last_check = datetime.utcnow()

        checks = {
            "environment": await self.check_environment(),
            "database": await self.check_database(),
            "telegram_api": await self.check_telegram_connection(),
        }

        all_healthy = all(checks.values())
        self.status = "healthy" if all_healthy else "unhealthy"

        return {
            "status": self.status,
            "timestamp": self.last_check.isoformat(),
            "checks": checks,
            "errors": self.errors,
        }

    def get_simple_status(self) -> str:
        """Получение простого статуса для HTTP endpoint"""
        if self.status == "healthy":
            return "OK"
        else:
            return f"ERROR: {'; '.join(self.errors)}"


# Глобальный экземпляр health checker
health_checker = HealthCheck()


class ErrorHandler:
    """Класс для обработки ошибок"""

    @staticmethod
    def log_error(error: Exception, context: str = ""):
        """Логирование ошибки"""
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)

    @staticmethod
    def format_user_error(error: Exception) -> str:
        """Форматирование ошибки для пользователя"""
        error_messages = {
            "FloodWaitError": "Временное ограничение Telegram API. Попробуйте позже.",
            "ChannelPrivateError": "Группа стала приватной или недоступной.",
            "ConnectionError": "Проблема с подключением. Попробуйте позже.",
            "TimeoutError": "Превышено время ожидания. Попробуйте позже.",
        }

        error_type = type(error).__name__
        return error_messages.get(
            error_type, "Произошла техническая ошибка. Попробуйте позже."
        )


def setup_error_logging():
    """Настройка логирования ошибок"""
    # Создание директории для логов
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)

    # Настройка файлового логгера
    file_handler = logging.FileHandler(
        os.path.join(logs_dir, f"bot_{datetime.now().strftime('%Y%m%d')}.log"),
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)

    # Формат логов
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Добавление обработчика к root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    logger.info("Error logging configured")
