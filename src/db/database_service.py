"""
Database service для работы с PostgreSQL
Асинхронный слой для Channel Analytics
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.dialects.postgresql import insert

from .models_new import Base, Channel, MemberDaily, ViewDaily, Post, Alert, ReportQueue

logger = logging.getLogger(__name__)

class DatabaseService:
    """Асинхронный сервис для работы с базой данных"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
    
    async def init_db(self):
        """Инициализация подключения к базе данных"""
        try:
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Логирование SQL запросов
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600
            )
            
            self.SessionLocal = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Создаем таблицы
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ База данных PostgreSQL успешно инициализирована")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """Контекстный менеджер для сессий"""
        async with self.SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    # === КАНАЛЫ ===
    
    async def add_channel(self, channel_id: int, username: str = None, 
                         title: str = None, description: str = None) -> Channel:
        """Добавление нового канала"""
        async with self.get_session() as session:
            # Проверяем, существует ли канал
            stmt = select(Channel).where(Channel.channel_id == channel_id)
            result = await session.execute(stmt)
            existing_channel = result.scalar_one_or_none()
            
            if existing_channel:
                # Обновляем существующий канал
                existing_channel.username = username or existing_channel.username
                existing_channel.title = title or existing_channel.title
                existing_channel.description = description or existing_channel.description
                existing_channel.is_active = True
                existing_channel.updated_at = datetime.utcnow()
                return existing_channel
            
            # Создаем новый канал
            channel = Channel(
                channel_id=channel_id,
                username=username,
                title=title,
                description=description
            )
            session.add(channel)
            await session.flush()
            
            logger.info(f"✅ Канал добавлен: {username or channel_id}")
            return channel
    
    async def get_channel(self, channel_id: int) -> Optional[Channel]:
        """Получение канала по ID"""
        async with self.get_session() as session:
            stmt = select(Channel).where(Channel.channel_id == channel_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_channel_by_username(self, username: str) -> Optional[Channel]:
        """Получение канала по username (без @, регистронезависимо)."""
        normalized_username = username.lstrip('@').strip().lower()
        if not normalized_username:
            return None

        async with self.get_session() as session:
            stmt = select(Channel).where(func.lower(Channel.username) == normalized_username)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    async def get_active_channels(self) -> List[Channel]:
        """Получение всех активных каналов"""
        async with self.get_session() as session:
            stmt = select(Channel).where(
                and_(Channel.is_active == True, Channel.monitoring_enabled == True)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def remove_channel(self, channel_id: int) -> bool:
        """Удаление канала (помечаем как неактивный)"""
        async with self.get_session() as session:
            stmt = select(Channel).where(Channel.channel_id == channel_id)
            result = await session.execute(stmt)
            channel = result.scalar_one_or_none()
            
            if channel:
                channel.is_active = False
                channel.monitoring_enabled = False
                channel.updated_at = datetime.utcnow()
                logger.info(f"✅ Канал отключен: {channel.username or channel_id}")
                return True
            return False
    
    # === СТАТИСТИКА ПОДПИСЧИКОВ ===
    
    async def add_members_stats(self, channel_id: int, date: date, 
                               members_count: int, members_growth: int = 0) -> MemberDaily:
        """Добавление статистики подписчиков за день"""
        async with self.get_session() as session:
            # Используем INSERT ... ON CONFLICT для PostgreSQL
            stmt = insert(MemberDaily).values(
                channel_id=channel_id,
                date=date,
                members_count=members_count,
                members_growth=members_growth,
                collected_at=datetime.utcnow()
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=['channel_id', 'date'],
                set_=dict(
                    members_count=stmt.excluded.members_count,
                    members_growth=stmt.excluded.members_growth,
                    collected_at=stmt.excluded.collected_at
                )
            )
            await session.execute(stmt)
            
            # Возвращаем обновленную запись
            select_stmt = select(MemberDaily).where(
                and_(MemberDaily.channel_id == channel_id, MemberDaily.date == date)
            )
            result = await session.execute(select_stmt)
            return result.scalar_one()
    
    async def get_members_history(self, channel_id: int, days: int = 30) -> List[MemberDaily]:
        """Получение истории подписчиков за последние дни"""
        async with self.get_session() as session:
            start_date = date.today() - timedelta(days=days)
            stmt = select(MemberDaily).where(
                and_(
                    MemberDaily.channel_id == channel_id,
                    MemberDaily.date >= start_date
                )
            ).order_by(MemberDaily.date)
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    # === СТАТИСТИКА ПРОСМОТРОВ ===
    
    async def add_views_stats(self, channel_id: int, date: date,
                             avg_views: int, total_views: int, posts_count: int) -> ViewDaily:
        """Добавление статистики просмотров за день"""
        async with self.get_session() as session:
            stmt = insert(ViewDaily).values(
                channel_id=channel_id,
                date=date,
                avg_views=avg_views,
                total_views=total_views,
                posts_count=posts_count,
                collected_at=datetime.utcnow()
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=['channel_id', 'date'],
                set_=dict(
                    avg_views=stmt.excluded.avg_views,
                    total_views=stmt.excluded.total_views,
                    posts_count=stmt.excluded.posts_count,
                    collected_at=stmt.excluded.collected_at
                )
            )
            await session.execute(stmt)
            
            select_stmt = select(ViewDaily).where(
                and_(ViewDaily.channel_id == channel_id, ViewDaily.date == date)
            )
            result = await session.execute(select_stmt)
            return result.scalar_one()
    
    # === ПОСТЫ ===
    
    async def add_post(self, channel_id: int, post_id: int, text: str = None,
                       views: int = 0, forwards: int = 0, posted_at: datetime = None) -> Post:
        """Добавление поста"""
        async with self.get_session() as session:
            stmt = insert(Post).values(
                channel_id=channel_id,
                post_id=post_id,
                text=text,
                views=views,
                forwards=forwards,
                posted_at=posted_at or datetime.utcnow()
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=['channel_id', 'post_id'],
                set_=dict(
                    views=stmt.excluded.views,
                    forwards=stmt.excluded.forwards
                )
            )
            await session.execute(stmt)
            
            select_stmt = select(Post).where(
                and_(Post.channel_id == channel_id, Post.post_id == post_id)
            )
            result = await session.execute(select_stmt)
            return result.scalar_one()
    
    # === АНАЛИТИКА ===
    
    async def get_channel_analytics(self, channel_id: int, days: int = 7) -> Dict[str, Any]:
        """Получение комплексной аналитики канала"""
        async with self.get_session() as session:
            # Получаем базовую информацию о канале
            channel_stmt = select(Channel).where(Channel.channel_id == channel_id)
            channel_result = await session.execute(channel_stmt)
            channel = channel_result.scalar_one_or_none()
            
            if not channel:
                return {}
            
            start_date = date.today() - timedelta(days=days)
            
            # История подписчиков
            members_stmt = select(MemberDaily).where(
                and_(
                    MemberDaily.channel_id == channel_id,
                    MemberDaily.date >= start_date
                )
            ).order_by(MemberDaily.date)
            members_result = await session.execute(members_stmt)
            members_history = members_result.scalars().all()
            
            # История просмотров
            views_stmt = select(ViewDaily).where(
                and_(
                    ViewDaily.channel_id == channel_id,
                    ViewDaily.date >= start_date
                )
            ).order_by(ViewDaily.date)
            views_result = await session.execute(views_stmt)
            views_history = views_result.scalars().all()

            # Все посты в периоде для детальной аналитики
            period_start_dt = datetime.combine(start_date, datetime.min.time())
            period_posts_stmt = select(Post).where(
                and_(
                    Post.channel_id == channel_id,
                    Post.posted_at >= period_start_dt
                )
            ).order_by(desc(Post.posted_at))
            period_posts_result = await session.execute(period_posts_stmt)
            period_posts = period_posts_result.scalars().all()
            
            # Последние посты
            posts_stmt = select(Post).where(
                Post.channel_id == channel_id
            ).order_by(desc(Post.posted_at)).limit(10)
            posts_result = await session.execute(posts_stmt)
            recent_posts = posts_result.scalars().all()

            # Периодные агрегаты подписчиков
            members_total_growth = 0
            members_growth_percent = 0.0
            avg_daily_growth = 0.0
            growth_days = 0
            decline_days = 0
            stable_days = 0

            if members_history:
                first_members = members_history[0].members_count
                last_members = members_history[-1].members_count
                members_total_growth = last_members - first_members
                if first_members > 0:
                    members_growth_percent = (members_total_growth / first_members) * 100

                members_growth_values = [int(item.members_growth or 0) for item in members_history]
                if members_growth_values:
                    avg_daily_growth = sum(members_growth_values) / len(members_growth_values)
                    growth_days = sum(1 for value in members_growth_values if value > 0)
                    decline_days = sum(1 for value in members_growth_values if value < 0)
                    stable_days = len(members_growth_values) - growth_days - decline_days

            # Периодные агрегаты просмотров и вовлеченности
            total_views_period = sum(int(item.total_views or 0) for item in views_history)
            total_posts_period = sum(int(item.posts_count or 0) for item in views_history)
            total_reactions_period = sum(int(item.total_reactions or 0) for item in views_history)
            total_forwards_period = sum(int(item.total_forwards or 0) for item in views_history)

            avg_views_per_post = (
                total_views_period / total_posts_period if total_posts_period > 0 else 0.0
            )
            avg_reactions_per_post = (
                total_reactions_period / total_posts_period if total_posts_period > 0 else 0.0
            )
            avg_forwards_per_post = (
                total_forwards_period / total_posts_period if total_posts_period > 0 else 0.0
            )

            # ER: реакция + репост от просмотров
            engagement_rate = (
                ((total_reactions_period + total_forwards_period) / total_views_period) * 100
                if total_views_period > 0 else 0.0
            )

            # Контент-микс по постам периода
            content_breakdown: Dict[str, Dict[str, float]] = {}
            posts_by_hour: Dict[int, Dict[str, float]] = {}
            posts_by_weekday: Dict[int, Dict[str, float]] = {}
            post_engagement_rates: List[float] = []
            top_posts: List[Dict[str, Any]] = []

            for post in period_posts:
                media_type = post.media_type or 'text'
                post_views = int(post.views or 0)
                post_forwards = int(post.forwards or 0)
                post_reactions = 0
                if isinstance(post.reactions, dict):
                    post_reactions = sum(int(value or 0) for value in post.reactions.values())

                if media_type not in content_breakdown:
                    content_breakdown[media_type] = {
                        'posts_count': 0,
                        'total_views': 0,
                        'total_reactions': 0,
                        'avg_views': 0.0,
                    }

                content_breakdown[media_type]['posts_count'] += 1
                content_breakdown[media_type]['total_views'] += post_views
                content_breakdown[media_type]['total_reactions'] += post_reactions

                hour = post.posted_at.hour
                if hour not in posts_by_hour:
                    posts_by_hour[hour] = {
                        'posts_count': 0,
                        'total_views': 0,
                    }
                posts_by_hour[hour]['posts_count'] += 1
                posts_by_hour[hour]['total_views'] += post_views

                weekday = post.posted_at.weekday()
                if weekday not in posts_by_weekday:
                    posts_by_weekday[weekday] = {
                        'posts_count': 0,
                        'total_views': 0,
                    }
                posts_by_weekday[weekday]['posts_count'] += 1
                posts_by_weekday[weekday]['total_views'] += post_views

                post_er = ((post_reactions + post_forwards) / post_views * 100) if post_views > 0 else 0.0
                if post_views > 0:
                    post_engagement_rates.append(post_er)
                top_posts.append(
                    {
                        'id': post.post_id,
                        'text': post.text[:120] + '...' if post.text and len(post.text) > 120 else post.text,
                        'views': post_views,
                        'forwards': post_forwards,
                        'reactions_count': post_reactions,
                        'engagement_rate': post_er,
                        'media_type': media_type,
                        'posted_at': post.posted_at.isoformat(),
                    }
                )

            for media_stats in content_breakdown.values():
                posts_count = int(media_stats['posts_count'])
                media_stats['avg_views'] = (
                    media_stats['total_views'] / posts_count if posts_count > 0 else 0.0
                )

            # Топ 5 постов по просмотрам
            top_posts = sorted(top_posts, key=lambda item: item['views'], reverse=True)[:5]

            best_posting_hour: Optional[int] = None
            best_posting_hour_avg_views = 0.0
            if posts_by_hour:
                best_hour, best_data = max(
                    posts_by_hour.items(),
                    key=lambda item: (
                        item[1]['total_views'] / item[1]['posts_count'] if item[1]['posts_count'] > 0 else 0
                    ),
                )
                best_posting_hour = int(best_hour)
                best_posting_hour_avg_views = (
                    best_data['total_views'] / best_data['posts_count']
                    if best_data['posts_count'] > 0 else 0.0
                )

            best_posting_weekday: Optional[int] = None
            best_posting_weekday_avg_views = 0.0
            if posts_by_weekday:
                best_wd, best_wd_data = max(
                    posts_by_weekday.items(),
                    key=lambda item: (
                        item[1]['total_views'] / item[1]['posts_count'] if item[1]['posts_count'] > 0 else 0
                    ),
                )
                best_posting_weekday = int(best_wd)
                best_posting_weekday_avg_views = (
                    best_wd_data['total_views'] / best_wd_data['posts_count']
                    if best_wd_data['posts_count'] > 0 else 0.0
                )

            # Расширенные ER-метрики:
            #   ER (classic) — (реакции + репосты) / подписчики * 100
            #   ERR          — (реакции + репосты) / просмотры  * 100  (= engagement_rate)
            #   VTR          — средний охват поста / подписчики * 100  (Reach Rate)
            current_subscribers = int(channel.subscribers_count or 0)
            avg_posts_per_day = total_posts_period / days if days > 0 else 0.0

            er_classic = (
                ((total_reactions_period + total_forwards_period) / current_subscribers) * 100
                if current_subscribers > 0 else 0.0
            )
            err = engagement_rate
            vtr = (
                (avg_views_per_post / current_subscribers) * 100
                if current_subscribers > 0 and avg_views_per_post > 0 else 0.0
            )
            avg_post_er = (
                sum(post_engagement_rates) / len(post_engagement_rates)
                if post_engagement_rates else 0.0
            )

            return {
                'channel': {
                    'id': channel.channel_id,
                    'username': channel.username,
                    'title': channel.title,
                    'subscribers': channel.subscribers_count,
                    'posts_count': channel.posts_count
                },
                'period': {
                    'days': days,
                    'start_date': start_date.isoformat(),
                    'members_total_growth': members_total_growth,
                    'members_growth_percent': members_growth_percent,
                    'avg_daily_growth': avg_daily_growth,
                    'growth_days': growth_days,
                    'decline_days': decline_days,
                    'stable_days': stable_days,
                    'total_posts': total_posts_period,
                    'total_views': total_views_period,
                    'total_reactions': total_reactions_period,
                    'total_forwards': total_forwards_period,
                    'avg_views_per_post': avg_views_per_post,
                    'avg_reactions_per_post': avg_reactions_per_post,
                    'avg_forwards_per_post': avg_forwards_per_post,
                    'engagement_rate': engagement_rate,
                    'er_classic': er_classic,
                    'err': err,
                    'vtr': vtr,
                    'avg_post_er': avg_post_er,
                    'avg_posts_per_day': avg_posts_per_day,
                    'current_subscribers': current_subscribers,
                    'best_posting_hour': best_posting_hour,
                    'best_posting_hour_avg_views': best_posting_hour_avg_views,
                    'best_posting_weekday': best_posting_weekday,
                    'best_posting_weekday_avg_views': best_posting_weekday_avg_views,
                },
                'members_history': [
                    {
                        'date': m.date.isoformat(),
                        'count': m.members_count,
                        'growth': m.members_growth
                    } for m in members_history
                ],
                'views_history': [
                    {
                        'date': v.date.isoformat(),
                        'avg_views': v.avg_views,
                        'total_views': v.total_views,
                        'posts_count': v.posts_count
                    } for v in views_history
                ],
                'recent_posts': [
                    {
                        'id': p.post_id,
                        'text': p.text[:100] + '...' if p.text and len(p.text) > 100 else p.text,
                        'views': p.views,
                        'forwards': p.forwards,
                        'posted_at': p.posted_at.isoformat()
                    } for p in recent_posts
                ],
                'top_posts': top_posts,
                'content_breakdown': content_breakdown,
                'posts_by_hour': {
                    int(hour): {
                        'posts_count': int(stats['posts_count']),
                        'avg_views': stats['total_views'] / stats['posts_count']
                        if stats['posts_count'] > 0 else 0.0,
                    }
                    for hour, stats in posts_by_hour.items()
                },
                'posts_by_weekday': {
                    int(weekday): {
                        'posts_count': int(stats['posts_count']),
                        'avg_views': stats['total_views'] / stats['posts_count']
                        if stats['posts_count'] > 0 else 0.0,
                    }
                    for weekday, stats in posts_by_weekday.items()
                },
            }
    
    async def close(self):
        """Закрытие подключения к базе данных"""
        if self.engine:
            await self.engine.dispose()
            logger.info("✅ Подключение к базе данных закрыто")
