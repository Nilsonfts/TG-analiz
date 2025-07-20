import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Float, 
    Boolean, Text, BigInteger, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Создание базового класса
Base = declarative_base()

class TelegramGroup(Base):
    """Модель для хранения информации о Telegram группах"""
    __tablename__ = 'telegram_groups'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    members_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    analytics = relationship("GroupAnalytics", back_populates="group")
    posts = relationship("GroupPost", back_populates="group")

class GroupAnalytics(Base):
    """Модель для хранения аналитических данных групп"""
    __tablename__ = 'group_analytics'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('telegram_groups.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    
    # Основные метрики
    members_count = Column(Integer, default=0)
    members_growth = Column(Integer, default=0)
    members_growth_percent = Column(Float, default=0.0)
    
    # Активность
    posts_count = Column(Integer, default=0)
    avg_views = Column(Float, default=0.0)
    avg_reactions = Column(Float, default=0.0)
    avg_comments = Column(Float, default=0.0)
    
    # Охваты
    total_views = Column(BigInteger, default=0)
    unique_views = Column(BigInteger, default=0)
    reach = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    group = relationship("TelegramGroup", back_populates="analytics")
    
    # Индексы
    __table_args__ = (
        Index('idx_group_date', 'group_id', 'date'),
    )

class GroupPost(Base):
    """Модель для хранения информации о постах в группах"""
    __tablename__ = 'group_posts'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('telegram_groups.id'), nullable=False)
    post_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    
    # Содержимое поста
    content_type = Column(String(50))  # text, photo, video, document, etc.
    text = Column(Text)
    media_count = Column(Integer, default=0)
    has_links = Column(Boolean, default=False)
    
    # Метрики
    views = Column(BigInteger, default=0)
    reactions_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    forwards_count = Column(Integer, default=0)
    
    # Временные метки
    post_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    group = relationship("TelegramGroup", back_populates="posts")
    reactions = relationship("PostReaction", back_populates="post")
    
    # Индексы
    __table_args__ = (
        Index('idx_group_post_date', 'group_id', 'post_date'),
        Index('idx_post_id_group', 'post_id', 'group_id'),
    )

class PostReaction(Base):
    """Модель для хранения реакций на посты"""
    __tablename__ = 'post_reactions'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('group_posts.id'), nullable=False)
    reaction_type = Column(String(50), nullable=False)  # like, dislike, love, etc.
    count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    post = relationship("GroupPost", back_populates="reactions")

class User(Base):
    """Модель для хранения пользователей бота"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    subscriptions = relationship("UserSubscription", back_populates="user")

class UserSubscription(Base):
    """Модель для хранения подписок пользователей на отчеты"""
    __tablename__ = 'user_subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subscription_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    chat_id = Column(BigInteger, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="subscriptions")
    
    # Индексы
    __table_args__ = (
        Index('idx_user_subscription_type', 'user_id', 'subscription_type'),
    )

class ContentAnalytics(Base):
    """Модель для аналитики по типам контента"""
    __tablename__ = 'content_analytics'
    
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey('telegram_groups.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    content_type = Column(String(50), nullable=False)
    
    # Метрики
    posts_count = Column(Integer, default=0)
    avg_views = Column(Float, default=0.0)
    avg_reactions = Column(Float, default=0.0)
    total_views = Column(BigInteger, default=0)
    total_reactions = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Индексы
    __table_args__ = (
        Index('idx_content_group_date', 'group_id', 'date', 'content_type'),
    )

# Создание движка и сессии
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/tg_analytics')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def init_db():
    """Инициализация базы данных"""
    # Создание всех таблиц
    Base.metadata.create_all(bind=engine)

def get_db():
    """Получение сессии базы данных"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

async def get_async_db():
    """Асинхронное получение сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
