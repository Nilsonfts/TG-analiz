"""
External API collectors for Telemetr and TGStat services.
"""
import aiohttp
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from src.config import settings
from src.collectors import BaseCollector, ChannelStats, PostData, MentionData

logger = logging.getLogger(__name__)


class TelemetrCollector(BaseCollector):
    """Collector for Telemetr.me API."""
    
    def __init__(self):
        super().__init__("telemetr", max_requests=30)  # Conservative rate limit
        self.api_key = settings.telemetr_api_key
        self.base_url = "https://api.telemetr.me/v1"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        """Ensure HTTP session is created."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=settings.request_timeout),
                headers={"User-Agent": "ChannelAnalytics/1.0"}
            )
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Make authenticated request to Telemetr API."""
        if not self.api_key:
            self.logger.warning("Telemetr API key not configured")
            return None
        
        await self._ensure_session()
        
        params = params or {}
        params["token"] = self.api_key
        
        try:
            async with self.session.get(f"{self.base_url}/{endpoint}", params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    self.logger.warning("Telemetr rate limit exceeded")
                    return None
                else:
                    self.logger.error(f"Telemetr API error {response.status}: {await response.text()}")
                    return None
        except Exception as e:
            self.logger.error(f"Telemetr request failed: {e}")
            return None
    
    async def collect_channel_stats(self, channel_id: int) -> Optional[ChannelStats]:
        """Collect channel statistics from Telemetr."""
        
        async def _collect():
            # Try to get channel info by ID or username
            channel_data = await self._make_request("channels/get", {"channel": str(channel_id)})
            
            if not channel_data or not channel_data.get("ok"):
                return None
            
            data = channel_data.get("result", {})
            
            stats = ChannelStats(
                channel_id=channel_id,
                title=data.get("title", ""),
                username=data.get("username"),
                description=data.get("description"),
                members_count=data.get("participants_count", 0),
                source="telemetr"
            )
            
            # Get additional metrics
            metrics_data = await self._make_request("channels/stat", {
                "channel": str(channel_id),
                "period": "day"
            })
            
            if metrics_data and metrics_data.get("ok"):
                metrics = metrics_data.get("result", {})
                
                stats.avg_views = metrics.get("avg_post_reach")
                stats.er_classic = metrics.get("err")
                stats.reach_24h = metrics.get("reach_24h")
                
                # Quality score if available
                if "quality" in metrics:
                    stats.quality_score = metrics["quality"]
            
            return stats
        
        return await self._with_rate_limit(_collect())
    
    async def collect_posts(self, channel_id: int, limit: int = 50) -> List[PostData]:
        """Collect posts from Telemetr."""
        
        async def _collect():
            posts_data = await self._make_request("channels/posts", {
                "channel": str(channel_id),
                "limit": min(limit, 100)  # API limit
            })
            
            if not posts_data or not posts_data.get("ok"):
                return []
            
            posts = []
            for post_info in posts_data.get("result", []):
                post = PostData(
                    channel_id=channel_id,
                    message_id=post_info.get("id", 0),
                    text=post_info.get("text"),
                    published_at=datetime.fromtimestamp(post_info.get("date", 0)),
                    views=post_info.get("views"),
                    reactions_count=post_info.get("reactions"),
                    forwards_count=post_info.get("forwards"),
                )
                posts.append(post)
            
            return posts
        
        return await self._with_rate_limit(_collect())
    
    async def collect_mentions(self, channel_id: int, days: int = 1) -> List[MentionData]:
        """Collect mentions from Telemetr."""
        
        async def _collect():
            mentions_data = await self._make_request("channels/mentions", {
                "channel": str(channel_id),
                "days": days
            })
            
            if not mentions_data or not mentions_data.get("ok"):
                return []
            
            mentions = []
            for mention_info in mentions_data.get("result", []):
                mention = MentionData(
                    channel_id=channel_id,
                    source_type="channel",  # Telemetr mainly tracks channels
                    source_id=mention_info.get("source_id"),
                    source_username=mention_info.get("source_username"),
                    source_title=mention_info.get("source_title"),
                    mention_text=mention_info.get("text"),
                    mentioned_at=datetime.fromtimestamp(mention_info.get("date", 0)),
                    views=mention_info.get("views"),
                    sentiment=mention_info.get("sentiment"),
                )
                mentions.append(mention)
            
            return mentions
        
        return await self._with_rate_limit(_collect())
    
    async def health_check(self) -> bool:
        """Check Telemetr API health."""
        if not self.api_key:
            return False
        
        try:
            result = await self._make_request("user/info")
            return result is not None and result.get("ok", False)
        except Exception:
            return False
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()


class TGStatCollector(BaseCollector):
    """Collector for TGStat.ru API."""
    
    def __init__(self):
        super().__init__("tgstat", max_requests=30)
        self.api_key = settings.tgstat_api_key
        self.base_url = "https://api.tgstat.ru"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        """Ensure HTTP session is created."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=settings.request_timeout),
                headers={
                    "User-Agent": "ChannelAnalytics/1.0",
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
                }
            )
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Make authenticated request to TGStat API."""
        if not self.api_key:
            self.logger.warning("TGStat API key not configured")
            return None
        
        await self._ensure_session()
        
        try:
            async with self.session.get(f"{self.base_url}/{endpoint}", params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    self.logger.warning("TGStat rate limit exceeded")
                    return None
                else:
                    self.logger.error(f"TGStat API error {response.status}: {await response.text()}")
                    return None
        except Exception as e:
            self.logger.error(f"TGStat request failed: {e}")
            return None
    
    async def collect_channel_stats(self, channel_id: int) -> Optional[ChannelStats]:
        """Collect channel statistics from TGStat."""
        
        async def _collect():
            # TGStat typically works with usernames, try to resolve
            channel_data = await self._make_request(f"channels/get", {"channelId": channel_id})
            
            if not channel_data or "error" in channel_data:
                return None
            
            data = channel_data.get("response", {})
            
            stats = ChannelStats(
                channel_id=channel_id,
                title=data.get("title", ""),
                username=data.get("username"),
                description=data.get("description"),
                members_count=data.get("participantsCount", 0),
                source="tgstat"
            )
            
            # Get analytics data
            analytics_data = await self._make_request(f"channels/stat", {
                "channelId": channel_id,
                "group": "day",
                "startDate": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "endDate": datetime.now().strftime("%Y-%m-%d")
            })
            
            if analytics_data and "response" in analytics_data:
                analytics = analytics_data["response"]
                
                if analytics:
                    latest = analytics[-1]  # Most recent data
                    stats.avg_views = latest.get("avgViews")
                    stats.er_classic = latest.get("errPercent")
                    
                    # Calculate growth
                    if len(analytics) > 1:
                        prev = analytics[-2]
                        current_members = latest.get("participantsCount", 0)
                        prev_members = prev.get("participantsCount", 0)
                        
                        if prev_members > 0:
                            stats.members_growth = current_members - prev_members
                            stats.members_growth_percent = (
                                (current_members - prev_members) / prev_members * 100
                            )
            
            return stats
        
        return await self._with_rate_limit(_collect())
    
    async def collect_posts(self, channel_id: int, limit: int = 50) -> List[PostData]:
        """Collect posts from TGStat."""
        
        async def _collect():
            posts_data = await self._make_request(f"channels/posts", {
                "channelId": channel_id,
                "limit": min(limit, 50),  # API limit
                "offset": 0
            })
            
            if not posts_data or "error" in posts_data:
                return []
            
            posts = []
            for post_info in posts_data.get("response", []):
                post = PostData(
                    channel_id=channel_id,
                    message_id=post_info.get("id", 0),
                    text=post_info.get("text"),
                    published_at=datetime.fromisoformat(
                        post_info.get("date", "").replace("Z", "+00:00")
                    ) if post_info.get("date") else datetime.utcnow(),
                    views=post_info.get("views"),
                )
                posts.append(post)
            
            return posts
        
        return await self._with_rate_limit(_collect())
    
    async def collect_mentions(self, channel_id: int, days: int = 1) -> List[MentionData]:
        """Collect mentions from TGStat."""
        
        async def _collect():
            # TGStat mentions API endpoint (if available)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            mentions_data = await self._make_request("channels/mentions", {
                "channelId": channel_id,
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d")
            })
            
            if not mentions_data or "error" in mentions_data:
                return []
            
            mentions = []
            for mention_info in mentions_data.get("response", []):
                mention = MentionData(
                    channel_id=channel_id,
                    source_type="channel",
                    source_id=mention_info.get("sourceChannelId"),
                    source_username=mention_info.get("sourceUsername"),
                    source_title=mention_info.get("sourceTitle"),
                    mention_text=mention_info.get("text"),
                    mentioned_at=datetime.fromisoformat(
                        mention_info.get("date", "").replace("Z", "+00:00")
                    ) if mention_info.get("date") else datetime.utcnow(),
                    views=mention_info.get("views"),
                )
                mentions.append(mention)
            
            return mentions
        
        return await self._with_rate_limit(_collect())
    
    async def health_check(self) -> bool:
        """Check TGStat API health."""
        if not self.api_key:
            return False
        
        try:
            result = await self._make_request("usage")
            return result is not None and "error" not in result
        except Exception:
            return False
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
