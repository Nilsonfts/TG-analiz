"""
Улучшенные модели базы данных для Channel Analytics
SQLAlchemy 2.x с асинхронной поддержкой
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, BigInteger, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

Base = declarative_base()

class Channel(Base):
    """Модель канала Telegram"""
    __tablename__ = 'channels'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Основные метрики
    subscribers_count: Mapped[int] = mapped_column(Integer, default=0)
    posts_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Статус и настройки
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связи
    members_daily: Mapped[List["MemberDaily"]] = relationship("MemberDaily", back_populates="channel", cascade="all, delete-orphan")
    views_daily: Mapped[List["ViewDaily"]] = relationship("ViewDaily", back_populates="channel", cascade="all, delete-orphan")
    posts: Mapped[List["Post"]] = relationship("Post", back_populates="channel", cascade="all, delete-orphan")

class MemberDaily(Base):
    """Ежедневная статистика подписчиков"""
    __tablename__ = 'members_daily'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('channels.channel_id'), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    
    # Метрики подписчиков
    members_count: Mapped[int] = mapped_column(Integer, default=0)
    members_growth: Mapped[int] = mapped_column(Integer, default=0)  # Прирост за день
    
    # Дополнительные метрики
    notifications_enabled: Mapped[int] = mapped_column(Integer, default=0)
    notifications_disabled: Mapped[int] = mapped_column(Integer, default=0)
    
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    channel: Mapped["Channel"] = relationship("Channel", back_populates="members_daily")

class ViewDaily(Base):
    """Ежедневная статистика просмотров"""
    __tablename__ = 'views_daily'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('channels.channel_id'), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    
    # Метрики просмотров
    avg_views: Mapped[int] = mapped_column(Integer, default=0)
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    posts_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Engagement метрики
    total_forwards: Mapped[int] = mapped_column(Integer, default=0)
    total_reactions: Mapped[int] = mapped_column(Integer, default=0)
    
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    channel: Mapped["Channel"] = relationship("Channel", back_populates="views_daily")

class Post(Base):
    """Детальная информация о постах"""
    __tablename__ = 'posts'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('channels.channel_id'), nullable=False, index=True)
    post_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    
    # Контент поста
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # photo, video, document
    
    # Метрики
    views: Mapped[int] = mapped_column(Integer, default=0)
    forwards: Mapped[int] = mapped_column(Integer, default=0)
    reactions: Mapped[dict] = mapped_column(JSON, default={})
    
    # Даты
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    channel: Mapped["Channel"] = relationship("Channel", back_populates="posts")

class Alert(Base):
    """Настройки алертов для каналов"""
    __tablename__ = 'alerts'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('channels.channel_id'), nullable=False)
    
    # Типы алертов
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'members_drop', 'views_drop', 'no_posts'
    threshold_value: Mapped[float] = mapped_column(Integer, nullable=False)  # Порог срабатывания
    
    # Настройки
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ReportQueue(Base):
    """Очередь отчетов для асинхронной обработки"""
    __tablename__ = 'reports_queue'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Тип отчета
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'daily', 'weekly', 'monthly'
    channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Параметры
    parameters: Mapped[dict] = mapped_column(JSON, default={})
    
    # Статус
    status: Mapped[str] = mapped_column(String(20), default='pending')  # pending, processing, completed, failed
    result_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Даты
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
