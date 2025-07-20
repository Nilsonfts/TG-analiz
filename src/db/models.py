"""
Database models for Channel Analytics.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, Integer, String, Text, 
    ForeignKey, Index, UniqueConstraint, func
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import JSONB

Base = declarative_base()


class Channel(Base):
    """Telegram channels being monitored."""
    
    __tablename__ = "channels"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    added_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    # Collection settings
    collect_posts: Mapped[bool] = mapped_column(Boolean, default=True)
    collect_stats: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    daily_stats: Mapped[List["MembersDaily"]] = relationship("MembersDaily", back_populates="channel")
    view_stats: Mapped[List["ViewsDaily"]] = relationship("ViewsDaily", back_populates="channel")
    posts: Mapped[List["Post"]] = relationship("Post", back_populates="channel")
    mentions: Mapped[List["Mention"]] = relationship("Mention", back_populates="channel")
    
    __table_args__ = (
        Index("idx_channel_username", "username"),
        Index("idx_channel_active", "is_active"),
    )


class MembersDaily(Base):
    """Daily member count statistics."""
    
    __tablename__ = "members_daily"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.channel_id"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    members_count: Mapped[int] = mapped_column(Integer, nullable=False)
    members_growth: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    members_growth_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Additional metrics
    online_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="daily_stats")
    
    __table_args__ = (
        UniqueConstraint("channel_id", "date", name="uq_members_daily_channel_date"),
        Index("idx_members_daily_channel_date", "channel_id", "date"),
        Index("idx_members_daily_date", "date"),
    )


class ViewsDaily(Base):
    """Daily views and engagement statistics."""
    
    __tablename__ = "views_daily"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.channel_id"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # View metrics
    avg_views: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    median_views: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reach_24h: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Engagement metrics
    er_classic: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Classic ER
    er_24h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)      # 24h ER
    total_reactions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_comments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_forwards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Post count
    posts_count: Mapped[int] = mapped_column(Integer, default=0)
    
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="view_stats")
    
    __table_args__ = (
        UniqueConstraint("channel_id", "date", name="uq_views_daily_channel_date"),
        Index("idx_views_daily_channel_date", "channel_id", "date"),
        Index("idx_views_daily_date", "date"),
    )


class Post(Base):
    """Individual channel posts archive."""
    
    __tablename__ = "posts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.channel_id"), nullable=False)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Post content
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # photo, video, document, etc.
    
    # Timing
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Metrics
    views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reactions_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comments_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    forwards_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Detailed reactions (JSON)
    reactions_detail: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="posts")
    
    __table_args__ = (
        UniqueConstraint("channel_id", "message_id", name="uq_posts_channel_message"),
        Index("idx_posts_channel_id", "channel_id"),
        Index("idx_posts_published_at", "published_at"),
        Index("idx_posts_views", "views"),
    )


class Mention(Base):
    """Channel mentions in Telegram."""
    
    __tablename__ = "mentions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.channel_id"), nullable=False)
    
    # Mention details
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # channel, group, bot
    source_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    source_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Mention content
    mention_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mention_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timing
    mentioned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Metrics
    views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # positive, negative, neutral
    
    # Relationships
    channel: Mapped["Channel"] = relationship("Channel", back_populates="mentions")
    
    __table_args__ = (
        Index("idx_mentions_channel_id", "channel_id"),
        Index("idx_mentions_mentioned_at", "mentioned_at"),
        Index("idx_mentions_source_type", "source_type"),
    )


class ReportsQueue(Base):
    """Queue for scheduled reports."""
    
    __tablename__ = "reports_queue"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # daily, weekly, monthly
    channel_ids: Mapped[Optional[List[int]]] = mapped_column(JSONB, nullable=True)  # None = all channels
    
    # Timing
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Execution
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Result
    report_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    file_paths: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    
    __table_args__ = (
        Index("idx_reports_queue_status", "status"),
        Index("idx_reports_queue_scheduled", "scheduled_for"),
        Index("idx_reports_queue_type", "report_type"),
    )


class QualityScore(Base):
    """Channel quality assessment scores."""
    
    __tablename__ = "quality_scores"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.channel_id"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Quality metrics
    content_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # 0-100
    engagement_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # 0-100
    growth_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)     # 0-100
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)      # 0-100
    
    # Source
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # internal, telemetr, tgstat
    source_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint("channel_id", "date", "source", name="uq_quality_scores_channel_date_source"),
        Index("idx_quality_scores_channel_date", "channel_id", "date"),
        Index("idx_quality_scores_overall", "overall_score"),
    )


# Database engine and session management
class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def create_tables(self):
        """Create all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self):
        """Drop all tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    async def get_session(self) -> AsyncSession:
        """Get async database session."""
        async with self.async_session() as session:
            yield session
    
    async def close(self):
        """Close database connection."""
        await self.engine.dispose()
