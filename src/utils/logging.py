"""
Structured logging configuration with Sentry integration.
"""
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from structlog.stdlib import LoggerFactory

from src.config import settings


def setup_logging():
    """Configure structured logging with Sentry integration."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add timestamp
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # JSON formatter for production, console for development
            structlog.dev.ConsoleRenderer(colors=not settings.debug) if settings.debug 
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Configure Sentry if DSN is provided
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            
            # Sentry logging integration
            sentry_logging = LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            )
            
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[
                    sentry_logging,
                    SqlalchemyIntegration(),
                ],
                # Set traces_sample_rate to 1.0 to capture 100%
                # of transactions for performance monitoring.
                traces_sample_rate=0.1 if not settings.debug else 0,
                # Set profiles_sample_rate to 1.0 to profile 100%
                # of sampled transactions.
                profiles_sample_rate=0.1 if not settings.debug else 0,
                environment="development" if settings.debug else "production",
                attach_stacktrace=True,
                send_default_pii=False,
            )
            
            # Add custom context
            sentry_sdk.set_context("application", {
                "name": "channel-analytics",
                "version": "2.0.0",
                "environment": "development" if settings.debug else "production"
            })
            
            logger = structlog.get_logger("sentry")
            logger.info("✅ Sentry integration enabled", dsn=settings.sentry_dsn[:20] + "...")
            
        except ImportError:
            logger = structlog.get_logger("sentry")
            logger.warning("❌ Sentry SDK not installed, error tracking disabled")
        except Exception as e:
            logger = structlog.get_logger("sentry")
            logger.error("❌ Failed to initialize Sentry", error=str(e))


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class TelegramLogHandler(logging.Handler):
    """Custom log handler that can send critical errors to Telegram."""
    
    def __init__(self, bot_token: str, chat_id: int, level=logging.ERROR):
        super().__init__(level)
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.last_sent = {}  # Rate limiting
    
    def emit(self, record: logging.LogRecord):
        """Send log record to Telegram if it's critical."""
        try:
            if record.levelno >= logging.ERROR:
                # Rate limiting: don't send same error more than once per hour
                error_key = f"{record.module}:{record.funcName}:{record.lineno}"
                now = datetime.utcnow()
                
                if error_key in self.last_sent:
                    time_diff = (now - self.last_sent[error_key]).total_seconds()
                    if time_diff < 3600:  # 1 hour
                        return
                
                self.last_sent[error_key] = now
                
                # Format error message
                message = f"🚨 <b>Error in Channel Analytics</b>\n\n"
                message += f"<b>Level:</b> {record.levelname}\n"
                message += f"<b>Module:</b> {record.module}\n"
                message += f"<b>Function:</b> {record.funcName}\n"
                message += f"<b>Line:</b> {record.lineno}\n\n"
                message += f"<b>Message:</b>\n<code>{record.getMessage()}</code>\n\n"
                
                if record.exc_info:
                    import traceback
                    exc_text = ''.join(traceback.format_exception(*record.exc_info))
                    # Truncate if too long
                    if len(exc_text) > 1000:
                        exc_text = exc_text[:1000] + "\n... (truncated)"
                    message += f"<b>Exception:</b>\n<code>{exc_text}</code>"
                
                message += f"\n<i>Time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
                
                # Send to Telegram (async, don't block)
                import asyncio
                try:
                    asyncio.create_task(self._send_to_telegram(message))
                except RuntimeError:
                    # No event loop running, skip
                    pass
        
        except Exception:
            # Don't let logging errors crash the application
            pass
    
    async def _send_to_telegram(self, message: str):
        """Send message to Telegram."""
        try:
            import aiohttp
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status != 200:
                        # Don't log this error to avoid recursion
                        pass
        
        except Exception:
            # Don't let Telegram errors crash the application
            pass


def setup_telegram_error_notifications(bot_token: str, admin_chat_id: int):
    """Setup Telegram notifications for critical errors."""
    try:
        telegram_handler = TelegramLogHandler(bot_token, admin_chat_id)
        
        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(telegram_handler)
        
        logger = get_logger("telegram_notifications")
        logger.info("✅ Telegram error notifications enabled", chat_id=admin_chat_id)
        
    except Exception as e:
        logger = get_logger("telegram_notifications")
        logger.error("❌ Failed to setup Telegram notifications", error=str(e))


class PerformanceLogger:
    """Context manager for performance logging."""
    
    def __init__(self, operation: str, logger: Optional[structlog.stdlib.BoundLogger] = None):
        self.operation = operation
        self.logger = logger or get_logger("performance")
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.debug("⏱️ Starting operation", operation=self.operation)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.utcnow() - self.start_time).total_seconds()
            
            if exc_type:
                self.logger.error(
                    "❌ Operation failed", 
                    operation=self.operation,
                    duration=f"{duration:.2f}s",
                    error=str(exc_val) if exc_val else "Unknown error"
                )
            else:
                level = "warning" if duration > 10 else "info" if duration > 1 else "debug"
                getattr(self.logger, level)(
                    "✅ Operation completed",
                    operation=self.operation,
                    duration=f"{duration:.2f}s"
                )


def log_function_call(func):
    """Decorator to log function calls with performance metrics."""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        with PerformanceLogger(f"{func.__name__}", logger):
            try:
                result = func(*args, **kwargs)
                logger.debug("Function call completed", function=func.__name__)
                return result
            except Exception as e:
                logger.error(
                    "Function call failed",
                    function=func.__name__,
                    error=str(e),
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )
                raise
    
    return wrapper


def log_async_function_call(func):
    """Decorator to log async function calls."""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        with PerformanceLogger(f"{func.__name__}", logger):
            try:
                result = await func(*args, **kwargs)
                logger.debug("Async function call completed", function=func.__name__)
                return result
            except Exception as e:
                logger.error(
                    "Async function call failed",
                    function=func.__name__,
                    error=str(e),
                    args_count=len(args),
                    kwargs_keys=list(kwargs.keys())
                )
                raise
    
    return wrapper


# Application-specific loggers
def get_collector_logger(collector_name: str) -> structlog.stdlib.BoundLogger:
    """Get logger for data collectors."""
    return get_logger(f"collector.{collector_name}")


def get_scheduler_logger() -> structlog.stdlib.BoundLogger:
    """Get logger for scheduler operations."""
    return get_logger("scheduler")


def get_report_logger() -> structlog.stdlib.BoundLogger:
    """Get logger for report generation."""
    return get_logger("reports")


def get_bot_logger() -> structlog.stdlib.BoundLogger:
    """Get logger for bot operations."""
    return get_logger("bot")


def get_db_logger() -> structlog.stdlib.BoundLogger:
    """Get logger for database operations."""
    return get_logger("database")


# Initialize logging on import
setup_logging()
