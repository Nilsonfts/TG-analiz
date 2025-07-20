import logging
from datetime import datetime, timedelta
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


class TelegramGroup:
    """Модель Telegram группы"""

    def __init__(
        self,
        group_id: int,
        username: str = None,
        title: str = None,
        description: str = None,
        members_count: int = 0,
        is_active: bool = True,
    ):
        self.group_id = group_id
        self.username = username
        self.title = title
        self.description = description
        self.members_count = members_count
        self.is_active = is_active


class UserSubscription:
    """Модель подписки пользователя"""

    def __init__(self, user_id: int, report_type: str, is_active: bool = True):
        self.user_id = user_id
        self.report_type = report_type
        self.is_active = is_active


class Database:
    """Класс для работы с базой данных"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None

    async def init_db(self):
        """Инициализация базы данных"""
        try:
            logger.info("Попытка подключения к базе данных...")
            logger.info(f"DATABASE_URL начинается с: {self.database_url[:20]}...")

            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=1, max_size=10, command_timeout=60
            )

            logger.info("✅ Пул подключений создан успешно")
            await self.create_tables()
            logger.info("✅ База данных успешно инициализирована")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            raise

    async def create_tables(self):
        """Создание таблиц"""
        async with self.pool.acquire() as conn:
            # Таблица групп
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_groups (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    title VARCHAR(255),
                    description TEXT,
                    members_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Таблица пользователей
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """
            )

            # Таблица сообщений
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    message_id BIGINT NOT NULL,
                    group_id BIGINT NOT NULL,
                    user_id BIGINT,
                    username VARCHAR(255),
                    text TEXT,
                    date TIMESTAMP NOT NULL,
                    reply_to_message_id BIGINT,
                    forward_from_user_id BIGINT,
                    views INTEGER DEFAULT 0,
                    reactions JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(message_id, group_id)
                )
            """
            )

            # Таблица подписок
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    report_type VARCHAR(50) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, report_type)
                )
            """
            )

            # Таблица аналитики
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_data (
                    id SERIAL PRIMARY KEY,
                    group_id BIGINT NOT NULL,
                    date DATE NOT NULL,
                    messages_count INTEGER DEFAULT 0,
                    users_count INTEGER DEFAULT 0,
                    active_users JSONB DEFAULT '[]',
                    top_users JSONB DEFAULT '[]',
                    hourly_activity JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(group_id, date)
                )
            """
            )

            # Индексы
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_group_date ON messages(group_id, date)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analytics_group_date ON analytics_data(group_id, date)"
            )

    async def add_group(self, group: TelegramGroup):
        """Добавление группы"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO telegram_groups (group_id, username, title, description, members_count, is_active)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (group_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    members_count = EXCLUDED.members_count,
                    updated_at = CURRENT_TIMESTAMP
            """,
                group.group_id,
                group.username,
                group.title,
                group.description,
                group.members_count,
                group.is_active,
            )

    async def get_active_groups(self) -> list[TelegramGroup]:
        """Получение активных групп"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM telegram_groups WHERE is_active = TRUE"
            )
            return [TelegramGroup(**dict(row)) for row in rows]

    async def save_messages(self, messages: list[dict[str, Any]]):
        """Сохранение сообщений"""
        async with self.pool.acquire() as conn:
            for message in messages:
                await conn.execute(
                    """
                    INSERT INTO messages (message_id, group_id, user_id, username, text, date,
                                        reply_to_message_id, forward_from_user_id, views, reactions)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (message_id, group_id) DO UPDATE SET
                        views = EXCLUDED.views,
                        reactions = EXCLUDED.reactions
                """,
                    message["message_id"],
                    message["group_id"],
                    message.get("user_id"),
                    message.get("username"),
                    message.get("text"),
                    message["date"],
                    message.get("reply_to_message_id"),
                    message.get("forward_from_user_id"),
                    message.get("views", 0),
                    message.get("reactions", {}),
                )

    async def get_daily_stats(self, group_id: int, date: datetime) -> dict[str, Any]:
        """Получение дневной статистики"""
        async with self.pool.acquire() as conn:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

            # Общее количество сообщений
            messages_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM messages
                WHERE group_id = $1 AND date >= $2 AND date < $3
            """,
                group_id,
                start_date,
                end_date,
            )

            # Количество уникальных пользователей
            users_count = await conn.fetchval(
                """
                SELECT COUNT(DISTINCT user_id) FROM messages
                WHERE group_id = $1 AND date >= $2 AND date < $3 AND user_id IS NOT NULL
            """,
                group_id,
                start_date,
                end_date,
            )

            # Топ пользователей
            top_users = await conn.fetch(
                """
                SELECT user_id, username, COUNT(*) as message_count
                FROM messages
                WHERE group_id = $1 AND date >= $2 AND date < $3 AND user_id IS NOT NULL
                GROUP BY user_id, username
                ORDER BY message_count DESC
                LIMIT 10
            """,
                group_id,
                start_date,
                end_date,
            )

            return {
                "messages_count": messages_count,
                "users_count": users_count,
                "top_users": [dict(row) for row in top_users],
            }

    async def subscribe_user(self, user_id: int, report_type: str):
        """Подписка пользователя на отчеты"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_subscriptions (user_id, report_type, is_active)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (user_id, report_type) DO UPDATE SET
                    is_active = TRUE
            """,
                user_id,
                report_type,
            )

    async def unsubscribe_user(self, user_id: int, report_type: str):
        """Отписка пользователя от отчетов"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_subscriptions
                SET is_active = FALSE
                WHERE user_id = $1 AND report_type = $2
            """,
                user_id,
                report_type,
            )

    async def get_subscribers(self, report_type: str) -> list[int]:
        """Получение подписчиков определенного типа отчетов"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id FROM user_subscriptions
                WHERE report_type = $1 AND is_active = TRUE
            """,
                report_type,
            )
            return [row["user_id"] for row in rows]

    async def save_user(self, user_id: int, username: str = None):
        """Сохранение пользователя в базе данных"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO telegram_users (user_id, username, first_seen)
                VALUES ($1, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    username = EXCLUDED.username,
                    last_seen = CURRENT_TIMESTAMP
            """,
                user_id,
                username,
            )

    async def get_users_count(self) -> int:
        """Получение количества пользователей"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM telegram_users")
            return result or 0

    async def get_recent_users(self, limit: int = 10) -> list[dict]:
        """Получение последних пользователей"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_id, username, first_seen, last_seen
                FROM telegram_users
                ORDER BY last_seen DESC
                LIMIT $1
            """,
                limit,
            )

            return [dict(row) for row in rows]

    async def close(self):
        """Закрытие соединений с базой данных"""
        if self.pool:
            await self.pool.close()

    async def get_group_by_id(self, group_id: int) -> TelegramGroup | None:
        """Получение группы по ID"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT group_id, username, title, description, members_count, is_active
                    FROM telegram_groups
                    WHERE group_id = $1
                """,
                    group_id,
                )

                if row:
                    return TelegramGroup(
                        group_id=row["group_id"],
                        username=row["username"],
                        title=row["title"],
                        description=row["description"],
                        members_count=row["members_count"],
                        is_active=row["is_active"],
                    )
                return None
        except Exception as e:
            logger.error(f"Ошибка получения группы по ID {group_id}: {e}")
            return None

    async def get_weekly_stats(self, group_id: int, start_date) -> dict[str, Any]:
        """Получение недельной статистики группы"""
        try:
            async with self.pool.acquire() as conn:
                end_date = start_date + timedelta(days=7)

                # Общее количество сообщений за неделю
                total_messages = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM messages
                    WHERE group_id = $1 AND date BETWEEN $2 AND $3
                """,
                    group_id,
                    start_date,
                    end_date,
                )

                # Количество активных пользователей
                total_active_users = await conn.fetchval(
                    """
                    SELECT COUNT(DISTINCT user_id) FROM messages
                    WHERE group_id = $1 AND date BETWEEN $2 AND $3
                """,
                    group_id,
                    start_date,
                    end_date,
                )

                # Новые пользователи (те, кто впервые написал в группе в этот период)
                new_users = await conn.fetchval(
                    """
                    SELECT COUNT(DISTINCT m.user_id)
                    FROM messages m
                    WHERE m.group_id = $1
                    AND m.date BETWEEN $2 AND $3
                    AND NOT EXISTS (
                        SELECT 1 FROM messages m2
                        WHERE m2.group_id = $1
                        AND m2.user_id = m.user_id
                        AND m2.date < $2
                    )
                """,
                    group_id,
                    start_date,
                    end_date,
                )

                return {
                    "total_messages": total_messages or 0,
                    "total_active_users": total_active_users or 0,
                    "new_users": new_users or 0,
                }
        except Exception as e:
            logger.error(f"Ошибка получения недельной статистики: {e}")
            return {}

    async def get_top_users(self, group_id: int, days: int = 7) -> list[dict[str, Any]]:
        """Получение топ пользователей по активности"""
        try:
            async with self.pool.acquire() as conn:
                start_date = datetime.now() - timedelta(days=days)

                rows = await conn.fetch(
                    """
                    SELECT
                        username,
                        COUNT(message_id) as message_count
                    FROM messages
                    WHERE group_id = $1 AND date >= $2 AND user_id IS NOT NULL
                    GROUP BY user_id, username
                    ORDER BY message_count DESC
                    LIMIT 10
                """,
                    group_id,
                    start_date,
                )

                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения топ пользователей: {e}")
            return []

    async def get_hourly_activity(
        self, group_id: int, days: int = 7
    ) -> list[dict[str, Any]]:
        """Получение активности по часам"""
        try:
            async with self.pool.acquire() as conn:
                start_date = datetime.now() - timedelta(days=days)

                rows = await conn.fetch(
                    """
                    SELECT
                        EXTRACT(HOUR FROM date) as hour,
                        COUNT(*) as message_count
                    FROM messages
                    WHERE group_id = $1 AND date >= $2
                    GROUP BY EXTRACT(HOUR FROM date)
                    ORDER BY hour
                """,
                    group_id,
                    start_date,
                )

                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения почасовой активности: {e}")
            return []

    async def get_daily_trend(
        self, group_id: int, days: int = 30
    ) -> list[dict[str, Any]]:
        """Получение тренда активности по дням"""
        try:
            async with self.pool.acquire() as conn:
                start_date = datetime.now() - timedelta(days=days)

                rows = await conn.fetch(
                    """
                    SELECT
                        DATE(date) as date,
                        COUNT(*) as message_count,
                        COUNT(DISTINCT user_id) as user_count
                    FROM messages
                    WHERE group_id = $1 AND date >= $2
                    GROUP BY DATE(date)
                    ORDER BY date
                """,
                    group_id,
                    start_date,
                )

                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения дневного тренда: {e}")
            return []

    async def get_group_summary_stats(self, group_id: int) -> dict[str, Any]:
        """Получение сводной статистики группы"""
        try:
            async with self.pool.acquire() as conn:
                # Общее количество сообщений
                total_messages = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM messages WHERE group_id = $1
                """,
                    group_id,
                )

                # Общее количество пользователей
                total_users = await conn.fetchval(
                    """
                    SELECT COUNT(DISTINCT user_id) FROM messages
                    WHERE group_id = $1 AND user_id IS NOT NULL
                """,
                    group_id,
                )

                # Топ пользователь
                top_user_row = await conn.fetchrow(
                    """
                    SELECT username, COUNT(*) as msg_count
                    FROM messages
                    WHERE group_id = $1 AND user_id IS NOT NULL
                    GROUP BY user_id, username
                    ORDER BY msg_count DESC
                    LIMIT 1
                """,
                    group_id,
                )

                # Статистика за последние 30 дней
                thirty_days_ago = datetime.now() - timedelta(days=30)
                recent_messages = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM messages
                    WHERE group_id = $1 AND date >= $2
                """,
                    group_id,
                    thirty_days_ago,
                )

                # Среднее сообщений в день (за последние 30 дней)
                avg_daily = recent_messages / 30 if recent_messages else 0

                # Информация о группе
                group_info = await conn.fetchrow(
                    """
                    SELECT title, members_count FROM telegram_groups WHERE group_id = $1
                """,
                    group_id,
                )

                return {
                    "total_messages": total_messages or 0,
                    "total_users": total_users or 0,
                    "top_user": top_user_row["username"] if top_user_row else "N/A",
                    "avg_daily": avg_daily,
                    "group_name": group_info["title"] if group_info else "Unknown",
                    "members_count": group_info["members_count"] if group_info else 0,
                    "period": "30 дней",
                }
        except Exception as e:
            logger.error(f"Ошибка получения сводной статистики: {e}")
            return {}
