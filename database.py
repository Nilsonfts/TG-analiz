import asyncpg
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TelegramGroup:
    """Модель Telegram группы"""
    def __init__(self, group_id: int, username: str = None, title: str = None, 
                 description: str = None, members_count: int = 0, is_active: bool = True):
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
    
    def _check_pool(self):
        """Проверка доступности пула подключений"""
        if not self.pool:
            raise RuntimeError("База данных не инициализирована или пул подключений недоступен")
    
    async def init_db(self):
        """Инициализация базы данных"""
        try:
            logger.info(f"Попытка подключения к базе данных...")
            logger.info(f"DATABASE_URL начинается с: {self.database_url[:20]}...")
            
            # Проверяем, что URL не None и не пустой
            if not self.database_url:
                raise ValueError("DATABASE_URL не установлен или пустой")
            
            logger.info("Создание пула подключений asyncpg...")
            # Сначала создаем пул
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            
            logger.info("✅ Пул подключений создан успешно")
            
            # Затем создаем таблицы
            logger.info("Создание таблиц...")
            try:
                await self.create_tables()
                logger.info("✅ База данных успешно инициализирована")
            except Exception as table_error:
                logger.warning(f"⚠️  Ошибка создания таблиц: {table_error}")
                logger.warning(f"⚠️  Тип ошибки таблиц: {type(table_error).__name__}")
                # Пул остается рабочим, но таблицы могут быть не созданы
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            logger.error(f"❌ Тип ошибки: {type(e).__name__}")
            logger.error(f"❌ Подробности: {str(e)}")
            if hasattr(e, '__traceback__'):
                import traceback
                logger.error(f"❌ Трассировка БД:\n{traceback.format_exc()}")
            raise
    
    async def create_tables(self):
        """Создание таблиц"""
        async with self.pool.acquire() as conn:
            # Таблица групп
            await conn.execute('''
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
            ''')
            
            # Таблица пользователей
            await conn.execute('''
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
            ''')
            
            # Таблица сообщений
            await conn.execute('''
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
            ''')
            
            # Таблица подписок
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    report_type VARCHAR(50) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, report_type)
                )
            ''')
            
            # Таблица аналитики
            await conn.execute('''
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
            ''')
            
            # Индексы
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_group_date ON messages(group_id, date)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_analytics_group_date ON analytics_data(group_id, date)')
    
    async def add_group(self, group: TelegramGroup):
        """Добавление группы"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO telegram_groups (group_id, username, title, description, members_count, is_active)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (group_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    members_count = EXCLUDED.members_count,
                    updated_at = CURRENT_TIMESTAMP
            ''', group.group_id, group.username, group.title, group.description, 
                group.members_count, group.is_active)
    
    async def get_active_groups(self) -> List[TelegramGroup]:
        """Получение активных групп"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM telegram_groups WHERE is_active = TRUE')
            return [TelegramGroup(**dict(row)) for row in rows]
    
    async def save_messages(self, messages: List[Dict[str, Any]]):
        """Сохранение сообщений"""
        async with self.pool.acquire() as conn:
            for message in messages:
                await conn.execute('''
                    INSERT INTO messages (message_id, group_id, user_id, username, text, date, 
                                        reply_to_message_id, forward_from_user_id, views, reactions)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (message_id, group_id) DO UPDATE SET
                        views = EXCLUDED.views,
                        reactions = EXCLUDED.reactions
                ''', message['message_id'], message['group_id'], message.get('user_id'),
                    message.get('username'), message.get('text'), message['date'],
                    message.get('reply_to_message_id'), message.get('forward_from_user_id'),
                    message.get('views', 0), message.get('reactions', {}))
    
    async def get_daily_stats(self, group_id: int, date: datetime) -> Dict[str, Any]:
        """Получение дневной статистики"""
        async with self.pool.acquire() as conn:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
            
            # Общее количество сообщений
            messages_count = await conn.fetchval('''
                SELECT COUNT(*) FROM messages 
                WHERE group_id = $1 AND date >= $2 AND date < $3
            ''', group_id, start_date, end_date)
            
            # Количество уникальных пользователей
            users_count = await conn.fetchval('''
                SELECT COUNT(DISTINCT user_id) FROM messages 
                WHERE group_id = $1 AND date >= $2 AND date < $3 AND user_id IS NOT NULL
            ''', group_id, start_date, end_date)
            
            # Топ пользователей
            top_users = await conn.fetch('''
                SELECT user_id, username, COUNT(*) as message_count
                FROM messages 
                WHERE group_id = $1 AND date >= $2 AND date < $3 AND user_id IS NOT NULL
                GROUP BY user_id, username
                ORDER BY message_count DESC
                LIMIT 10
            ''', group_id, start_date, end_date)
            
            return {
                'messages_count': messages_count,
                'users_count': users_count,
                'top_users': [dict(row) for row in top_users]
            }
    
    async def subscribe_user(self, user_id: int, report_type: str):
        """Подписка пользователя на отчеты"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO user_subscriptions (user_id, report_type, is_active)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (user_id, report_type) DO UPDATE SET
                    is_active = TRUE
            ''', user_id, report_type)
    
    async def unsubscribe_user(self, user_id: int, report_type: str):
        """Отписка пользователя от отчетов"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE user_subscriptions 
                SET is_active = FALSE 
                WHERE user_id = $1 AND report_type = $2
            ''', user_id, report_type)
    
    async def get_subscribers(self, report_type: str) -> List[int]:
        """Получение подписчиков определенного типа отчетов"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT user_id FROM user_subscriptions 
                WHERE report_type = $1 AND is_active = TRUE
            ''', report_type)
            return [row['user_id'] for row in rows]
    
    async def save_user(self, user_id: int, username: str = None):
        """Сохранение пользователя в базе данных"""
        try:
            self._check_pool()
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO telegram_users (user_id, username, first_seen)
                    VALUES ($1, $2, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        username = EXCLUDED.username,
                        last_seen = CURRENT_TIMESTAMP
                ''', user_id, username)
                logger.info(f"Пользователь {user_id} ({username}) сохранен успешно")
        except Exception as e:
            logger.error(f"Ошибка сохранения пользователя {user_id}: {e}")
            raise
    
    async def get_users_count(self) -> int:
        """Получение количества пользователей"""
        try:
            self._check_pool()
            async with self.pool.acquire() as conn:
                result = await conn.fetchval('SELECT COUNT(*) FROM telegram_users')
                return result or 0
        except Exception as e:
            logger.error(f"Ошибка получения количества пользователей: {e}")
            return 0
    
    async def get_recent_users(self, limit: int = 10) -> List[Dict]:
        """Получение последних пользователей"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT user_id, username, first_seen, last_seen 
                FROM telegram_users 
                ORDER BY last_seen DESC 
                LIMIT $1
            ''', limit)
            
            return [dict(row) for row in rows]
    
    async def close(self):
        """Закрытие соединений с базой данных"""
        if self.pool:
            await self.pool.close()
