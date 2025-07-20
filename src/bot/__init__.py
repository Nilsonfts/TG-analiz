"""
Main bot initialization and configuration.
"""
import asyncio
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import settings
from src.db.models import DatabaseManager
from src.handlers import router, init_services
from src.scheduler import SchedulerService
from src.utils.logging import get_bot_logger, setup_telegram_error_notifications

logger = get_bot_logger()


class ChannelAnalyticsBot:
    """Main bot class with all components."""
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.scheduler: Optional[SchedulerService] = None
        self._running = False
    
    async def initialize(self):
        """Initialize all bot components."""
        logger.info("🚀 Initializing Channel Analytics Bot...")
        
        # Initialize bot and dispatcher
        self.bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
                link_preview_is_disabled=True
            )
        )
        
        self.dp = Dispatcher()
        self.dp.include_router(router)
        
        # Initialize database
        self.db_manager = DatabaseManager(settings.database_url)
        
        # Create tables if they don't exist
        try:
            await self.db_manager.create_tables()
            logger.info("✅ Database tables initialized")
        except Exception as e:
            logger.error("❌ Failed to initialize database", error=str(e))
            raise
        
        # Initialize services
        init_services(self.db_manager)
        
        # Initialize scheduler
        self.scheduler = SchedulerService(self.db_manager)
        
        # Setup error notifications if admin chat is configured
        if settings.admin_user_ids and settings.bot_token:
            # Use first admin as error notification recipient
            admin_chat_id = settings.admin_user_ids[0]
            setup_telegram_error_notifications(settings.bot_token, admin_chat_id)
        
        logger.info("✅ Bot initialization completed")
    
    async def start(self):
        """Start the bot and all services."""
        if self._running:
            logger.warning("Bot is already running")
            return
        
        try:
            logger.info("🚀 Starting Channel Analytics Bot...")
            
            # Start scheduler
            await self.scheduler.start()
            
            # Start bot polling
            self._running = True
            
            # Drop pending updates and start polling
            await self.bot.delete_webhook(drop_pending_updates=True)
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error("❌ Failed to start bot", error=str(e))
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the bot and all services."""
        if not self._running:
            return
        
        logger.info("⏹️ Stopping Channel Analytics Bot...")
        
        try:
            # Stop scheduler
            if self.scheduler:
                await self.scheduler.stop()
            
            # Stop bot
            if self.dp:
                await self.dp.stop_polling()
            
            # Close database connections
            if self.db_manager:
                await self.db_manager.close()
            
            # Close bot session
            if self.bot:
                await self.bot.session.close()
            
            self._running = False
            logger.info("✅ Bot stopped successfully")
        
        except Exception as e:
            logger.error("❌ Error during bot shutdown", error=str(e))
    
    async def send_report_to_chat(self, report_data: dict, chat_id: Optional[int] = None):
        """Send generated report to specified chat."""
        if not chat_id:
            chat_id = settings.report_chat_id
        
        if not chat_id:
            logger.warning("No report chat ID configured")
            return
        
        try:
            # Send markdown report
            await self.bot.send_message(
                chat_id=chat_id,
                text=report_data["markdown"],
                parse_mode=ParseMode.HTML
            )
            
            # Send charts if available
            if "charts" in report_data and report_data["charts"]:
                for chart_path in report_data["charts"]:
                    try:
                        from aiogram.types import FSInputFile
                        chart_file = FSInputFile(chart_path)
                        await self.bot.send_photo(
                            chat_id=chat_id,
                            photo=chart_file
                        )
                    except Exception as e:
                        logger.error("Failed to send chart", error=str(e), chart=chart_path)
            
            logger.info("Report sent to chat", chat_id=chat_id, report_type=report_data.get("type"))
        
        except Exception as e:
            logger.error("Failed to send report to chat", error=str(e), chat_id=chat_id)
    
    async def send_alert(self, alert_data: dict, chat_id: Optional[int] = None):
        """Send alert notification to chat."""
        if not chat_id:
            chat_id = settings.report_chat_id
        
        if not chat_id:
            return
        
        try:
            alert_text = (
                f"🚨 <b>Алерт: Резкое падение метрик</b>\n\n"
                f"📺 <b>Канал:</b> {alert_data.get('channel_title', 'Неизвестно')}\n"
                f"🆔 <b>ID:</b> <code>{alert_data.get('channel_id')}</code>\n\n"
                f"📉 <b>ER вчера:</b> {alert_data.get('yesterday_er', 0):.1f}%\n"
                f"📉 <b>ER сегодня:</b> {alert_data.get('today_er', 0):.1f}%\n"
                f"📊 <b>Падение:</b> {alert_data.get('drop_percent', 0):.1f}%\n\n"
                f"⚠️ <i>Требуется проверка канала</i>"
            )
            
            await self.bot.send_message(
                chat_id=chat_id,
                text=alert_text,
                parse_mode=ParseMode.HTML
            )
            
            logger.info("Alert sent", channel_id=alert_data.get('channel_id'))
        
        except Exception as e:
            logger.error("Failed to send alert", error=str(e))


# Global bot instance
bot_instance: Optional[ChannelAnalyticsBot] = None


async def get_bot() -> ChannelAnalyticsBot:
    """Get or create bot instance."""
    global bot_instance
    
    if not bot_instance:
        bot_instance = ChannelAnalyticsBot()
        await bot_instance.initialize()
    
    return bot_instance


async def start_bot():
    """Start the bot (main entry point)."""
    bot = await get_bot()
    await bot.start()


async def stop_bot():
    """Stop the bot."""
    global bot_instance
    
    if bot_instance:
        await bot_instance.stop()
        bot_instance = None


# Health check functions for Railway
async def health_check() -> dict:
    """Get bot health status."""
    global bot_instance
    
    if not bot_instance:
        return {
            "status": "stopped",
            "bot": False,
            "database": False,
            "scheduler": False
        }
    
    # Check database
    db_healthy = False
    try:
        async with bot_instance.db_manager.async_session() as session:
            from sqlalchemy import select
            await session.execute(select(1))
            db_healthy = True
    except Exception:
        pass
    
    # Check scheduler
    scheduler_healthy = bot_instance.scheduler and bot_instance.scheduler._running
    
    return {
        "status": "running" if bot_instance._running else "stopped",
        "bot": bot_instance._running,
        "database": db_healthy,
        "scheduler": scheduler_healthy,
        "services": {
            "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else "localhost",  # Hide credentials
            "admin_users_count": len(settings.admin_user_ids),
            "telemetr_configured": bool(settings.telemetr_api_key),
            "tgstat_configured": bool(settings.tgstat_api_key),
            "report_chat_configured": bool(settings.report_chat_id)
        }
    }
