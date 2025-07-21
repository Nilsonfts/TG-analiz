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
            
            # Последние посты
            posts_stmt = select(Post).where(
                Post.channel_id == channel_id
            ).order_by(desc(Post.posted_at)).limit(10)
            posts_result = await session.execute(posts_stmt)
            recent_posts = posts_result.scalars().all()
            
            return {
                'channel': {
                    'id': channel.channel_id,
                    'username': channel.username,
                    'title': channel.title,
                    'subscribers': channel.subscribers_count,
                    'posts_count': channel.posts_count
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
                ]
            }
    
    async def close(self):
        """Закрытие подключения к базе данных"""
        if self.engine:
            await self.engine.dispose()
            logger.info("✅ Подключение к базе данных закрыто")
