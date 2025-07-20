"""
Telegram collector using Telethon for channel data collection.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from telethon import TelegramClient
from telethon.errors import ChannelPrivateError, FloodWaitError, ChatAdminRequiredError
from telethon.tl.types import Channel, Chat, MessageMediaPhoto, MessageMediaDocument

from src.config import settings
from src.collectors import BaseCollector, ChannelStats, PostData, MentionData

import logging
logger = logging.getLogger(__name__)


class TelegramCollector(BaseCollector):
    """Collector for Telegram channels using Telethon."""
    
    def __init__(self):
        super().__init__("telegram", max_requests=settings.telegram_api_limit)
        self.client: Optional[TelegramClient] = None
        self._connected = False
    
    async def _ensure_connected(self):
        """Ensure Telegram client is connected."""
        if not self._connected:
            await self._connect()
    
    async def _connect(self):
        """Connect to Telegram."""
        try:
            self.client = TelegramClient(
                "channel_analytics_session",
                settings.telegram_api_id,
                settings.telegram_api_hash
            )
            await self.client.start()
            self._connected = True
            self.logger.info("✅ Telegram client connected successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Telegram: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Telegram."""
        if self.client and self._connected:
            await self.client.disconnect()
            self._connected = False
            self.logger.info("🔌 Telegram client disconnected")
    
    async def collect_channel_stats(self, channel_id: int) -> Optional[ChannelStats]:
        """Collect channel statistics."""
        await self._ensure_connected()
        
        async def _collect():
            try:
                # Get channel entity
                entity = await self.client.get_entity(channel_id)
                
                if not isinstance(entity, Channel):
                    self.logger.warning(f"Entity {channel_id} is not a channel")
                    return None
                
                # Get full channel info
                full_channel = await self.client(
                    functions.channels.GetFullChannelRequest(entity)
                )
                
                # Calculate basic stats
                stats = ChannelStats(
                    channel_id=channel_id,
                    title=entity.title,
                    username=getattr(entity, 'username', None),
                    description=getattr(full_channel.full_chat, 'about', None),
                    members_count=getattr(full_channel.full_chat, 'participants_count', 0),
                    online_count=getattr(full_channel.full_chat, 'online_count', None),
                    source="telegram"
                )
                
                # Get recent posts for metrics calculation
                recent_posts = await self._get_recent_posts(entity, limit=20)
                if recent_posts:
                    await self._calculate_engagement_metrics(stats, recent_posts)
                
                return stats
                
            except ChannelPrivateError:
                self.logger.error(f"Channel {channel_id} is private or bot is not a member")
                return None
            except ChatAdminRequiredError:
                self.logger.error(f"Admin rights required for channel {channel_id}")
                return None
            except FloodWaitError as e:
                self.logger.warning(f"Flood wait for {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
                raise
            except Exception as e:
                self.logger.error(f"Error collecting stats for {channel_id}: {e}")
                return None
        
        return await self._with_rate_limit(_collect())
    
    async def collect_posts(self, channel_id: int, limit: int = 50) -> List[PostData]:
        """Collect recent posts from channel."""
        await self._ensure_connected()
        
        async def _collect():
            try:
                entity = await self.client.get_entity(channel_id)
                posts = []
                
                async for message in self.client.iter_messages(entity, limit=limit):
                    if message.text is None and message.media is None:
                        continue
                    
                    # Determine media type
                    media_type = None
                    if message.media:
                        if isinstance(message.media, MessageMediaPhoto):
                            media_type = "photo"
                        elif isinstance(message.media, MessageMediaDocument):
                            media_type = "document"
                        else:
                            media_type = "other"
                    
                    # Extract reactions
                    reactions_count = 0
                    reactions_detail = {}
                    if hasattr(message, 'reactions') and message.reactions:
                        for reaction in message.reactions.results:
                            reactions_count += reaction.count
                            emoji = getattr(reaction.reaction, 'emoticon', str(reaction.reaction))
                            reactions_detail[emoji] = reaction.count
                    
                    post = PostData(
                        channel_id=channel_id,
                        message_id=message.id,
                        text=message.text,
                        media_type=media_type,
                        published_at=message.date,
                        views=getattr(message, 'views', None),
                        reactions_count=reactions_count if reactions_count > 0 else None,
                        reactions_detail=reactions_detail if reactions_detail else None,
                        # Note: Telegram doesn't provide comments/forwards count via Bot API
                        comments_count=None,
                        forwards_count=getattr(message, 'forwards', None),
                    )
                    posts.append(post)
                
                return posts
                
            except Exception as e:
                self.logger.error(f"Error collecting posts for {channel_id}: {e}")
                return []
        
        return await self._with_rate_limit(_collect())
    
    async def collect_mentions(self, channel_id: int, days: int = 1) -> List[MentionData]:
        """Collect mentions of the channel."""
        await self._ensure_connected()
        
        # Note: This is a simplified implementation
        # Real mention detection would require searching across multiple channels
        # which is complex and requires specific permissions
        
        async def _collect():
            mentions = []
            
            try:
                entity = await self.client.get_entity(channel_id)
                channel_username = getattr(entity, 'username', None)
                
                if not channel_username:
                    self.logger.warning(f"Channel {channel_id} has no username, cannot search mentions")
                    return mentions
                
                # Search for mentions in public channels (limited scope)
                # This is a simplified implementation
                search_query = f"@{channel_username}"
                
                # For a full implementation, you would need to:
                # 1. Search across multiple known channels
                # 2. Use search APIs if available
                # 3. Monitor specific channels for mentions
                
                self.logger.info(f"Mention collection for @{channel_username} - limited implementation")
                
            except Exception as e:
                self.logger.error(f"Error collecting mentions for {channel_id}: {e}")
            
            return mentions
        
        return await self._with_rate_limit(_collect())
    
    async def health_check(self) -> bool:
        """Check if Telegram collector is working."""
        try:
            await self._ensure_connected()
            if self.client and self._connected:
                # Try to get own info as a simple test
                me = await self.client.get_me()
                return me is not None
            return False
        except Exception as e:
            self.logger.error(f"Telegram health check failed: {e}")
            return False
    
    async def _get_recent_posts(self, entity, limit: int = 20):
        """Get recent posts for calculations."""
        posts = []
        try:
            async for message in self.client.iter_messages(entity, limit=limit):
                if message.text or message.media:
                    posts.append(message)
            return posts
        except Exception as e:
            self.logger.error(f"Error getting recent posts: {e}")
            return []
    
    async def _calculate_engagement_metrics(self, stats: ChannelStats, posts):
        """Calculate engagement metrics from posts."""
        if not posts:
            return
        
        views = [getattr(msg, 'views', 0) for msg in posts if getattr(msg, 'views', 0) > 0]
        reactions = []
        
        for msg in posts:
            msg_reactions = 0
            if hasattr(msg, 'reactions') and msg.reactions:
                for reaction in msg.reactions.results:
                    msg_reactions += reaction.count
            reactions.append(msg_reactions)
        
        if views:
            stats.avg_views = sum(views) / len(views)
            stats.median_views = sorted(views)[len(views) // 2]
            stats.total_views = sum(views)
        
        if reactions and stats.members_count > 0:
            total_reactions = sum(reactions)
            stats.total_reactions = total_reactions
            
            # Calculate ER (Engagement Rate)
            if stats.avg_views and stats.avg_views > 0:
                stats.er_classic = (total_reactions / len(posts)) / stats.avg_views * 100
            
            # 24h ER approximation (using recent posts as proxy)
            recent_24h_posts = [p for p in posts if (datetime.utcnow() - p.date).days < 1]
            if recent_24h_posts:
                recent_reactions = sum(
                    sum(r.count for r in msg.reactions.results) 
                    if hasattr(msg, 'reactions') and msg.reactions else 0
                    for msg in recent_24h_posts
                )
                recent_views = sum(
                    getattr(msg, 'views', 0) for msg in recent_24h_posts
                )
                if recent_views > 0:
                    stats.er_24h = (recent_reactions / recent_views) * 100


# Import Telethon functions
try:
    from telethon.tl import functions
except ImportError:
    logger.warning("Telethon functions not available - some features may be limited")
