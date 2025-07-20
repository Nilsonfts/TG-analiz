import asyncpg
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TelegramChannel:
    """Модель Telegram канала"""
    def __init__(self, channel_id: int, username: str = None, title: str = None, 
                 description: str = None, subscribers_count: int = 0, 
                 posts_count: int = 0, is_active: bool = True):
        self.channel_id = channel_id
        self.username = username
        self.title = title
        self.description = description
        self.subscribers_count = subscribers_count
        self.posts_count = posts_count
        self.is_active = is_active

class ChannelAnalytics:
    """Класс для аналитики Telegram каналов"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
    
    async def init_db(self):
        """Инициализация базы данных для каналов"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            
            await self.create_channel_tables()
            logger.info("✅ База данных каналов успешно инициализирована")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД каналов: {e}")
            raise
    
    async def create_channel_tables(self):
        """Создание таблиц для аналитики каналов"""
        async with self.pool.acquire() as conn:
            # Таблица каналов
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS telegram_channels (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    title VARCHAR(255),
                    description TEXT,
                    subscribers_count INTEGER DEFAULT 0,
                    posts_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица постов канала
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS channel_posts (
                    id SERIAL PRIMARY KEY,
                    post_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    message_id BIGINT,
                    text TEXT,
                    views_count INTEGER DEFAULT 0,
                    forwards_count INTEGER DEFAULT 0,
                    reactions JSONB DEFAULT '{}',
                    publish_date TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(post_id, channel_id)
                )
            ''')
            
            # Таблица аналитики подписчиков
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS subscriber_analytics (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT NOT NULL,
                    date DATE NOT NULL,
                    subscribers_gained INTEGER DEFAULT 0,
                    subscribers_lost INTEGER DEFAULT 0,
                    total_subscribers INTEGER DEFAULT 0,
                    notifications_enabled INTEGER DEFAULT 0,
                    notifications_disabled INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(channel_id, date)
                )
            ''')
            
            # Таблица аналитики просмотров
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS views_analytics (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT NOT NULL,
                    date DATE NOT NULL,
                    hour_of_day INTEGER NOT NULL,
                    post_views INTEGER DEFAULT 0,
                    story_views INTEGER DEFAULT 0,
                    unique_viewers INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(channel_id, date, hour_of_day)
                )
            ''')
            
            # Таблица источников трафика
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS traffic_sources (
                    id SERIAL PRIMARY KEY,
                    channel_id BIGINT NOT NULL,
                    date DATE NOT NULL,
                    source_type VARCHAR(50) NOT NULL, -- 'url', 'search', 'groups', 'channels', 'private_chats', 'other'
                    subscribers_count INTEGER DEFAULT 0,
                    views_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(channel_id, date, source_type)
                )
            ''')
            
            # Индексы
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_channel_posts_date ON channel_posts(channel_id, publish_date)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_subscriber_analytics_date ON subscriber_analytics(channel_id, date)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_views_analytics_date ON views_analytics(channel_id, date)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_traffic_sources_date ON traffic_sources(channel_id, date)')

    async def add_channel(self, channel: TelegramChannel):
        """Добавление канала"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO telegram_channels (channel_id, username, title, description, subscribers_count, posts_count, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (channel_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    subscribers_count = EXCLUDED.subscribers_count,
                    posts_count = EXCLUDED.posts_count,
                    updated_at = CURRENT_TIMESTAMP
            ''', channel.channel_id, channel.username, channel.title, channel.description, 
                channel.subscribers_count, channel.posts_count, channel.is_active)

    async def get_active_channels(self) -> List[TelegramChannel]:
        """Получение активных каналов"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM telegram_channels WHERE is_active = TRUE')
            return [TelegramChannel(
                channel_id=row['channel_id'],
                username=row['username'],
                title=row['title'],
                description=row['description'],
                subscribers_count=row['subscribers_count'],
                posts_count=row['posts_count'],
                is_active=row['is_active']
            ) for row in rows]

    async def get_channel_by_id(self, channel_id: int) -> Optional[TelegramChannel]:
        """Получение канала по ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM telegram_channels WHERE channel_id = $1
            ''', channel_id)
            
            if row:
                return TelegramChannel(
                    channel_id=row['channel_id'],
                    username=row['username'],
                    title=row['title'],
                    description=row['description'],
                    subscribers_count=row['subscribers_count'],
                    posts_count=row['posts_count'],
                    is_active=row['is_active']
                )
            return None

    async def get_channel_summary(self, channel_id: int) -> Dict[str, Any]:
        """Получение сводной статистики канала"""
        async with self.pool.acquire() as conn:
            # Основная информация о канале
            channel_info = await conn.fetchrow('''
                SELECT title, subscribers_count, posts_count 
                FROM telegram_channels WHERE channel_id = $1
            ''', channel_id)
            
            if not channel_info:
                return {}
            
            # Статистика за последние 7 дней
            week_ago = datetime.now().date() - timedelta(days=7)
            
            # Прирост подписчиков за неделю
            subscriber_growth = await conn.fetchval('''
                SELECT COALESCE(SUM(subscribers_gained - subscribers_lost), 0)
                FROM subscriber_analytics 
                WHERE channel_id = $1 AND date >= $2
            ''', channel_id, week_ago)
            
            # Процент роста
            current_subscribers = channel_info['subscribers_count']
            growth_percentage = (subscriber_growth / current_subscribers * 100) if current_subscribers > 0 else 0
            
            # Общие просмотры за неделю
            total_views = await conn.fetchval('''
                SELECT COALESCE(SUM(post_views), 0)
                FROM views_analytics 
                WHERE channel_id = $1 AND date >= $2
            ''', channel_id, week_ago)
            
            # Просмотры историй за неделю
            story_views = await conn.fetchval('''
                SELECT COALESCE(SUM(story_views), 0)
                FROM views_analytics 
                WHERE channel_id = $1 AND date >= $2
            ''', channel_id, week_ago)
            
            # Реакции на посты за неделю
            reactions_data = await conn.fetchval('''
                SELECT COUNT(*) 
                FROM channel_posts 
                WHERE channel_id = $1 AND publish_date >= $2
                AND jsonb_array_length(COALESCE(reactions, '[]'::jsonb)) > 0
            ''', channel_id, week_ago)
            
            # Уведомления (последние данные)
            notifications_data = await conn.fetchrow('''
                SELECT notifications_enabled, notifications_disabled, total_subscribers
                FROM subscriber_analytics 
                WHERE channel_id = $1 
                ORDER BY date DESC LIMIT 1
            ''', channel_id)
            
            notifications_enabled_percent = 0
            if notifications_data and notifications_data['total_subscribers'] > 0:
                notifications_enabled_percent = (
                    notifications_data['notifications_enabled'] / 
                    notifications_data['total_subscribers'] * 100
                )
            
            return {
                'title': channel_info['title'],
                'subscribers_count': current_subscribers,
                'posts_count': channel_info['posts_count'],
                'subscriber_growth': subscriber_growth,
                'growth_percentage': growth_percentage,
                'total_views': total_views,
                'story_views': story_views,
                'reactions_count': reactions_data or 0,
                'notifications_enabled_percent': notifications_enabled_percent,
                'period_days': 7
            }

    async def get_subscriber_growth_data(self, channel_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Получение данных роста подписчиков"""
        async with self.pool.acquire() as conn:
            start_date = datetime.now().date() - timedelta(days=days)
            
            rows = await conn.fetch('''
                SELECT date, subscribers_gained, subscribers_lost, total_subscribers
                FROM subscriber_analytics 
                WHERE channel_id = $1 AND date >= $2
                ORDER BY date
            ''', channel_id, start_date)
            
            return [dict(row) for row in rows]

    async def get_hourly_views_data(self, channel_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Получение данных просмотров по часам"""
        async with self.pool.acquire() as conn:
            start_date = datetime.now().date() - timedelta(days=days)
            
            rows = await conn.fetch('''
                SELECT hour_of_day, SUM(post_views) as total_views
                FROM views_analytics 
                WHERE channel_id = $1 AND date >= $2
                GROUP BY hour_of_day
                ORDER BY hour_of_day
            ''', channel_id, start_date)
            
            return [dict(row) for row in rows]

    async def get_traffic_sources_data(self, channel_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Получение данных источников трафика"""
        async with self.pool.acquire() as conn:
            start_date = datetime.now().date() - timedelta(days=days)
            
            rows = await conn.fetch('''
                SELECT source_type, SUM(subscribers_count) as total_subscribers, SUM(views_count) as total_views
                FROM traffic_sources 
                WHERE channel_id = $1 AND date >= $2
                GROUP BY source_type
                ORDER BY total_subscribers DESC
            ''', channel_id, start_date)
            
            return [dict(row) for row in rows]

    async def generate_recommendations(self, channel_id: int) -> List[str]:
        """Генерация AI-рекомендаций для канала"""
        try:
            summary = await self.get_channel_summary(channel_id)
            recommendations = []
            
            # Анализ роста подписчиков
            if summary.get('growth_percentage', 0) < 5:
                recommendations.append("🔥 Стимулируйте обсуждения - активность низкая")
                recommendations.append("📢 Используйте призывы к действию в постах")
            
            # Анализ вовлеченности
            if summary.get('notifications_enabled_percent', 0) < 50:
                recommendations.append("👥 Низкая вовлечённость - привлекайте участников")
                recommendations.append("🔔 Мотивируйте подписчиков включить уведомления")
            
            # Анализ просмотров
            subscribers = summary.get('subscribers_count', 1)
            views = summary.get('total_views', 0)
            if views < subscribers * 0.3:  # Менее 30% охвата
                recommendations.append("📈 Низкий охват - оптимизируйте время публикации")
                recommendations.append("⏰ Анализируйте пиковые часы активности аудитории")
            
            # Анализ контента
            if summary.get('reactions_count', 0) < summary.get('posts_count', 1) * 0.1:
                recommendations.append("💬 Мало реакций - создавайте более интерактивный контент")
                recommendations.append("🎯 Задавайте вопросы и проводите опросы")
            
            if not recommendations:
                recommendations.append("✅ Отличные показатели! Продолжайте в том же духе")
                recommendations.append("🚀 Экспериментируйте с новыми форматами контента")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Ошибка генерации рекомендаций: {e}")
            return ["❌ Ошибка анализа данных"]

    async def close(self):
        """Закрытие соединений с базой данных"""
        if self.pool:
            await self.pool.close()
