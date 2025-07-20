"""
Scheduler service for automated data collection and report generation.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config import settings
from src.db.models import DatabaseManager, Channel, MembersDaily, ViewsDaily, ReportsQueue
from src.collectors import CompositeCollector
from src.collectors.telegram_collector import TelegramCollector
from src.collectors.external_collectors import TelemetrCollector, TGStatCollector

logger = logging.getLogger(__name__)


class SchedulerService:
    """Main scheduler service for automated tasks."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone="UTC"
        )
        
        # Initialize collectors
        collectors = [TelegramCollector()]
        if settings.telemetr_api_key:
            collectors.append(TelemetrCollector())
        if settings.tgstat_api_key:
            collectors.append(TGStatCollector())
        
        self.collector = CompositeCollector(collectors)
        
        self._running = False
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            return
        
        logger.info("🕒 Starting scheduler service...")
        
        # Schedule daily data collection
        self.scheduler.add_job(
            self._daily_data_collection,
            CronTrigger(
                hour=settings.daily_job_hour,
                minute=0,
                timezone="UTC"
            ),
            id="daily_collection",
            name="Daily Data Collection",
            replace_existing=True
        )
        
        # Schedule weekly reports
        self.scheduler.add_job(
            self._weekly_report_generation,
            CronTrigger(
                day_of_week="mon",
                hour=settings.weekly_job_hour,
                minute=0,
                timezone="UTC"
            ),
            id="weekly_reports",
            name="Weekly Report Generation",
            replace_existing=True
        )
        
        # Schedule monthly reports
        self.scheduler.add_job(
            self._monthly_report_generation,
            CronTrigger(
                day=1,
                hour=settings.monthly_job_hour,
                minute=0,
                timezone="UTC"
            ),
            id="monthly_reports",
            name="Monthly Report Generation",
            replace_existing=True
        )
        
        # Schedule health monitoring
        self.scheduler.add_job(
            self._health_monitoring,
            IntervalTrigger(hours=1),
            id="health_monitoring",
            name="Health Monitoring",
            replace_existing=True
        )
        
        # Schedule alerts checking
        self.scheduler.add_job(
            self._check_alerts,
            IntervalTrigger(hours=6),
            id="alerts_checking",
            name="Alerts Checking",
            replace_existing=True
        )
        
        self.scheduler.start()
        self._running = True
        
        logger.info("✅ Scheduler service started successfully")
        logger.info(f"📅 Daily collection: {settings.daily_job_hour:02d}:00 UTC")
        logger.info(f"📊 Weekly reports: Monday {settings.weekly_job_hour:02d}:00 UTC")
        logger.info(f"📈 Monthly reports: 1st day {settings.monthly_job_hour:02d}:00 UTC")
    
    async def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return
        
        logger.info("⏹️ Stopping scheduler service...")
        self.scheduler.shutdown(wait=True)
        self._running = False
        logger.info("✅ Scheduler service stopped")
    
    async def _daily_data_collection(self):
        """Daily data collection job."""
        logger.info("🔄 Starting daily data collection...")
        
        start_time = datetime.utcnow()
        collected_channels = 0
        failed_channels = 0
        
        try:
            async with self.db_manager.async_session() as session:
                # Get all active channels
                result = await session.execute(
                    select(Channel).where(Channel.is_active == True)
                )
                channels = result.scalars().all()
                
                logger.info(f"📊 Collecting data for {len(channels)} channels...")
                
                for channel in channels:
                    try:
                        await self._collect_channel_data(session, channel)
                        collected_channels += 1
                        
                        # Rate limiting between channels
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to collect data for channel {channel.channel_id}: {e}")
                        failed_channels += 1
                
                await session.commit()
        
        except Exception as e:
            logger.error(f"❌ Daily collection failed: {e}")
            return
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"✅ Daily collection completed in {duration:.1f}s: "
            f"{collected_channels} successful, {failed_channels} failed"
        )
    
    async def _collect_channel_data(self, session: AsyncSession, channel: Channel):
        """Collect data for a single channel."""
        logger.debug(f"📥 Collecting data for channel {channel.channel_id}")
        
        # Collect channel stats
        stats = await self.collector.collect_channel_stats(channel.channel_id)
        if not stats:
            logger.warning(f"No stats collected for channel {channel.channel_id}")
            return
        
        # Update channel info
        channel.title = stats.title
        channel.username = stats.username
        channel.description = stats.description
        
        # Save daily member stats
        today = datetime.utcnow().date()
        
        # Check if we already have data for today
        existing_members = await session.execute(
            select(MembersDaily).where(
                MembersDaily.channel_id == channel.channel_id,
                MembersDaily.date == today
            )
        )
        existing_member_record = existing_members.scalar_one_or_none()
        
        if existing_member_record:
            # Update existing record
            existing_member_record.members_count = stats.members_count
            existing_member_record.online_count = stats.online_count
            existing_member_record.members_growth = stats.members_growth
            existing_member_record.members_growth_percent = stats.members_growth_percent
        else:
            # Create new record
            member_stats = MembersDaily(
                channel_id=channel.channel_id,
                date=today,
                members_count=stats.members_count,
                online_count=stats.online_count,
                members_growth=stats.members_growth,
                members_growth_percent=stats.members_growth_percent
            )
            session.add(member_stats)
        
        # Save daily view stats
        existing_views = await session.execute(
            select(ViewsDaily).where(
                ViewsDaily.channel_id == channel.channel_id,
                ViewsDaily.date == today
            )
        )
        existing_view_record = existing_views.scalar_one_or_none()
        
        if existing_view_record:
            # Update existing record
            existing_view_record.avg_views = stats.avg_views
            existing_view_record.median_views = stats.median_views
            existing_view_record.total_views = stats.total_views
            existing_view_record.reach_24h = stats.reach_24h
            existing_view_record.er_classic = stats.er_classic
            existing_view_record.er_24h = stats.er_24h
            existing_view_record.total_reactions = stats.total_reactions
            existing_view_record.total_comments = stats.total_comments
            existing_view_record.total_forwards = stats.total_forwards
        else:
            # Create new record
            view_stats = ViewsDaily(
                channel_id=channel.channel_id,
                date=today,
                avg_views=stats.avg_views,
                median_views=stats.median_views,
                total_views=stats.total_views,
                reach_24h=stats.reach_24h,
                er_classic=stats.er_classic,
                er_24h=stats.er_24h,
                total_reactions=stats.total_reactions,
                total_comments=stats.total_comments,
                total_forwards=stats.total_forwards
            )
            session.add(view_stats)
        
        # Collect and save posts if enabled
        if channel.collect_posts:
            await self._collect_channel_posts(session, channel)
    
    async def _collect_channel_posts(self, session: AsyncSession, channel: Channel):
        """Collect posts for a channel."""
        try:
            posts = await self.collector.collect_posts(channel.channel_id, limit=20)
            
            for post_data in posts:
                # Check if post already exists
                from src.db.models import Post
                existing = await session.execute(
                    select(Post).where(
                        Post.channel_id == channel.channel_id,
                        Post.message_id == post_data.message_id
                    )
                )
                existing_post = existing.scalar_one_or_none()
                
                if existing_post:
                    # Update metrics (views, reactions can change)
                    existing_post.views = post_data.views
                    existing_post.reactions_count = post_data.reactions_count
                    existing_post.comments_count = post_data.comments_count
                    existing_post.forwards_count = post_data.forwards_count
                    existing_post.reactions_detail = post_data.reactions_detail
                else:
                    # Create new post
                    post = Post(
                        channel_id=channel.channel_id,
                        message_id=post_data.message_id,
                        text=post_data.text,
                        media_type=post_data.media_type,
                        published_at=post_data.published_at,
                        views=post_data.views,
                        reactions_count=post_data.reactions_count,
                        comments_count=post_data.comments_count,
                        forwards_count=post_data.forwards_count,
                        reactions_detail=post_data.reactions_detail
                    )
                    session.add(post)
        
        except Exception as e:
            logger.error(f"Failed to collect posts for channel {channel.channel_id}: {e}")
    
    async def _weekly_report_generation(self):
        """Generate weekly reports."""
        logger.info("📊 Generating weekly reports...")
        
        try:
            async with self.db_manager.async_session() as session:
                # Get all active channels
                result = await session.execute(
                    select(Channel).where(Channel.is_active == True)
                )
                channels = result.scalars().all()
                
                # Create report queue entry
                report_queue = ReportsQueue(
                    report_type="weekly",
                    channel_ids=[ch.channel_id for ch in channels],
                    scheduled_for=datetime.utcnow(),
                    status="pending"
                )
                session.add(report_queue)
                await session.commit()
                
                logger.info(f"📋 Queued weekly report for {len(channels)} channels")
        
        except Exception as e:
            logger.error(f"❌ Failed to queue weekly reports: {e}")
    
    async def _monthly_report_generation(self):
        """Generate monthly reports."""
        logger.info("📈 Generating monthly reports...")
        
        try:
            async with self.db_manager.async_session() as session:
                # Get all active channels
                result = await session.execute(
                    select(Channel).where(Channel.is_active == True)
                )
                channels = result.scalars().all()
                
                # Create report queue entry
                report_queue = ReportsQueue(
                    report_type="monthly",
                    channel_ids=[ch.channel_id for ch in channels],
                    scheduled_for=datetime.utcnow(),
                    status="pending"
                )
                session.add(report_queue)
                await session.commit()
                
                logger.info(f"📋 Queued monthly report for {len(channels)} channels")
        
        except Exception as e:
            logger.error(f"❌ Failed to queue monthly reports: {e}")
    
    async def _health_monitoring(self):
        """Monitor system health."""
        logger.debug("🏥 Checking system health...")
        
        try:
            # Check collector health
            collector_healthy = await self.collector.health_check()
            
            # Check database health
            async with self.db_manager.async_session() as session:
                await session.execute(select(1))
                db_healthy = True
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            db_healthy = False
        
        if not collector_healthy:
            logger.warning("⚠️ Collector health check failed")
        
        if not db_healthy:
            logger.error("❌ Database health check failed")
        
        if collector_healthy and db_healthy:
            logger.debug("✅ All systems healthy")
    
    async def _check_alerts(self):
        """Check for alert conditions (e.g., ER drop)."""
        logger.debug("🚨 Checking alert conditions...")
        
        try:
            async with self.db_manager.async_session() as session:
                # Check for significant ER drops in the last 24 hours
                yesterday = datetime.utcnow().date() - timedelta(days=1)
                today = datetime.utcnow().date()
                
                # Get yesterday's and today's ER data
                result = await session.execute(
                    select(ViewsDaily).where(
                        ViewsDaily.date.in_([yesterday, today]),
                        ViewsDaily.er_classic.isnot(None)
                    )
                )
                
                er_data = {}
                for record in result.scalars().all():
                    if record.channel_id not in er_data:
                        er_data[record.channel_id] = {}
                    er_data[record.channel_id][record.date] = record.er_classic
                
                # Check for drops > 30%
                alerts = []
                for channel_id, dates in er_data.items():
                    if yesterday in dates and today in dates:
                        yesterday_er = dates[yesterday]
                        today_er = dates[today]
                        
                        if yesterday_er > 0:
                            drop_percent = ((yesterday_er - today_er) / yesterday_er) * 100
                            if drop_percent > 30:  # More than 30% drop
                                alerts.append({
                                    "channel_id": channel_id,
                                    "yesterday_er": yesterday_er,
                                    "today_er": today_er,
                                    "drop_percent": drop_percent
                                })
                
                if alerts:
                    logger.warning(f"🚨 {len(alerts)} channels with significant ER drops detected")
                    # TODO: Send alert notifications
                else:
                    logger.debug("✅ No alert conditions detected")
        
        except Exception as e:
            logger.error(f"❌ Alert checking failed: {e}")
    
    def get_job_status(self) -> dict:
        """Get status of scheduled jobs."""
        if not self._running:
            return {"status": "stopped"}
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "status": "running",
            "jobs": jobs
        }
    
    async def trigger_manual_collection(self, channel_ids: Optional[List[int]] = None):
        """Manually trigger data collection."""
        logger.info("🔄 Manual data collection triggered")
        
        try:
            async with self.db_manager.async_session() as session:
                if channel_ids:
                    # Collect specific channels
                    result = await session.execute(
                        select(Channel).where(
                            Channel.channel_id.in_(channel_ids),
                            Channel.is_active == True
                        )
                    )
                else:
                    # Collect all active channels
                    result = await session.execute(
                        select(Channel).where(Channel.is_active == True)
                    )
                
                channels = result.scalars().all()
                
                for channel in channels:
                    await self._collect_channel_data(session, channel)
                
                await session.commit()
                
                logger.info(f"✅ Manual collection completed for {len(channels)} channels")
                return len(channels)
        
        except Exception as e:
            logger.error(f"❌ Manual collection failed: {e}")
            raise
