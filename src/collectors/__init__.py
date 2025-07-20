"""
Abstract collector interface and implementations for various data sources.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class ChannelStats:
    """Standardized channel statistics."""
    channel_id: int
    title: str
    username: Optional[str]
    description: Optional[str]
    members_count: int
    online_count: Optional[int] = None
    
    # Growth metrics
    members_growth: Optional[int] = None
    members_growth_percent: Optional[float] = None
    
    # View metrics
    avg_views: Optional[float] = None
    median_views: Optional[float] = None
    total_views: Optional[int] = None
    reach_24h: Optional[int] = None
    
    # Engagement metrics
    er_classic: Optional[float] = None
    er_24h: Optional[float] = None
    total_reactions: Optional[int] = None
    total_comments: Optional[int] = None
    total_forwards: Optional[int] = None
    
    # Quality metrics
    quality_score: Optional[float] = None
    
    # Metadata
    collected_at: datetime = None
    source: str = "unknown"
    
    def __post_init__(self):
        if self.collected_at is None:
            self.collected_at = datetime.utcnow()


@dataclass
class PostData:
    """Standardized post data."""
    channel_id: int
    message_id: int
    text: Optional[str]
    media_type: Optional[str]
    published_at: datetime
    views: Optional[int] = None
    reactions_count: Optional[int] = None
    comments_count: Optional[int] = None
    forwards_count: Optional[int] = None
    reactions_detail: Optional[Dict[str, int]] = None
    collected_at: datetime = None
    
    def __post_init__(self):
        if self.collected_at is None:
            self.collected_at = datetime.utcnow()


@dataclass
class MentionData:
    """Standardized mention data."""
    channel_id: int
    source_type: str
    source_id: Optional[int]
    source_username: Optional[str]
    source_title: Optional[str]
    mention_text: Optional[str]
    mention_context: Optional[str]
    mentioned_at: datetime
    views: Optional[int] = None
    sentiment: Optional[str] = None
    collected_at: datetime = None
    
    def __post_init__(self):
        if self.collected_at is None:
            self.collected_at = datetime.utcnow()


class Collector(Protocol):
    """Abstract collector interface."""
    
    @abstractmethod
    async def collect_channel_stats(self, channel_id: int) -> Optional[ChannelStats]:
        """Collect channel statistics."""
        pass
    
    @abstractmethod
    async def collect_posts(self, channel_id: int, limit: int = 50) -> List[PostData]:
        """Collect recent posts."""
        pass
    
    @abstractmethod
    async def collect_mentions(self, channel_id: int, days: int = 1) -> List[MentionData]:
        """Collect channel mentions."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if collector is working."""
        pass


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, max_requests: int, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def acquire(self):
        """Acquire rate limit permission."""
        now = datetime.utcnow()
        
        # Remove old requests
        self.requests = [
            req_time for req_time in self.requests 
            if (now - req_time).total_seconds() < self.time_window
        ]
        
        # Check if we can make a request
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0]).total_seconds()
            if sleep_time > 0:
                logger.info(f"Rate limit hit, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
        
        self.requests.append(now)


class BaseCollector(ABC):
    """Base collector with common functionality."""
    
    def __init__(self, name: str, max_requests: int = 60):
        self.name = name
        self.rate_limiter = RateLimiter(max_requests)
        self.logger = logging.getLogger(f"collector.{name}")
    
    async def _with_rate_limit(self, coro):
        """Execute coroutine with rate limiting."""
        await self.rate_limiter.acquire()
        try:
            return await coro
        except Exception as e:
            self.logger.error(f"Error in {self.name} collector: {e}")
            raise
    
    async def _exponential_backoff(self, func, max_retries: int = 3):
        """Execute function with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                sleep_time = 2 ** attempt
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {self.name}, "
                    f"retrying in {sleep_time}s: {e}"
                )
                await asyncio.sleep(sleep_time)


class CompositeCollector:
    """Collector that combines multiple data sources."""
    
    def __init__(self, collectors: List[Collector]):
        self.collectors = collectors
        self.logger = logging.getLogger("collector.composite")
    
    async def collect_channel_stats(self, channel_id: int) -> Optional[ChannelStats]:
        """Collect stats from the first available collector."""
        for collector in self.collectors:
            try:
                if await collector.health_check():
                    stats = await collector.collect_channel_stats(channel_id)
                    if stats:
                        return stats
            except Exception as e:
                self.logger.warning(f"Collector {collector.__class__.__name__} failed: {e}")
                continue
        
        self.logger.error(f"No collector could provide stats for channel {channel_id}")
        return None
    
    async def collect_posts(self, channel_id: int, limit: int = 50) -> List[PostData]:
        """Collect posts from all available collectors."""
        all_posts = []
        
        for collector in self.collectors:
            try:
                if await collector.health_check():
                    posts = await collector.collect_posts(channel_id, limit)
                    all_posts.extend(posts)
            except Exception as e:
                self.logger.warning(f"Collector {collector.__class__.__name__} failed: {e}")
                continue
        
        # Deduplicate by message_id
        seen_ids = set()
        unique_posts = []
        for post in all_posts:
            if post.message_id not in seen_ids:
                unique_posts.append(post)
                seen_ids.add(post.message_id)
        
        return unique_posts[:limit]
    
    async def collect_mentions(self, channel_id: int, days: int = 1) -> List[MentionData]:
        """Collect mentions from all available collectors."""
        all_mentions = []
        
        for collector in self.collectors:
            try:
                if await collector.health_check():
                    mentions = await collector.collect_mentions(channel_id, days)
                    all_mentions.extend(mentions)
            except Exception as e:
                self.logger.warning(f"Collector {collector.__class__.__name__} failed: {e}")
                continue
        
        return all_mentions
    
    async def health_check(self) -> bool:
        """Check if any collector is working."""
        for collector in self.collectors:
            try:
                if await collector.health_check():
                    return True
            except Exception:
                continue
        return False
