#!/usr/bin/env python3
"""
Channel Analytics Bot v2.0 - Professional Telegram Channel Analytics System

Main application entry point with HTTP health server and bot integration.
"""
import asyncio
import json
import logging
import os
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import settings
from src.bot import start_bot, stop_bot, health_check
from src.utils.logging import get_logger

logger = get_logger("main")


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for Railway health checks and status endpoints."""
    
    def log_message(self, format: str, *args: Any) -> None:
        """Disable HTTP server logs to reduce noise."""
        pass
    
    def do_GET(self) -> None:
        """Handle GET requests for health checks and status."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        if self.path == "/health":
            # Simple health check for Railway
            response = {
                "status": "healthy",
                "service": "channel-analytics-bot",
                "version": "2.0.0",
                "timestamp": asyncio.get_event_loop().time() if hasattr(asyncio, '_get_running_loop') and asyncio._get_running_loop() else 0,
                "message": "Service is running"
            }
        
        elif self.path == "/status":
            # Basic status
            response = {
                "service": "channel-analytics-bot",
                "version": "2.0.0",
                "status": "running",
                "environment": "development" if settings.debug else "production",
                "endpoints": {
                    "/health": "Detailed health check",
                    "/status": "Basic status",
                    "/": "Service info"
                }
            }
        
        else:
            # Service info
            response = {
                "name": "🤖 Channel Analytics Bot",
                "version": "2.0.0",
                "description": "Professional Telegram Channel Analytics System",
                "features": [
                    "Multi-channel monitoring",
                    "Automated data collection",
                    "Chart generation",
                    "CSV export",
                    "Alert system",
                    "PostgreSQL storage",
                    "Railway deployment"
                ],
                "endpoints": {
                    "/health": "Health check",
                    "/status": "Status info",
                    "/": "This page"
                },
                "documentation": "https://github.com/Nilsonfts/TG-analiz"
            }
        
        self.wfile.write(json.dumps(response, indent=2, ensure_ascii=False).encode('utf-8'))


def start_http_server():
    """Start HTTP server for Railway health checks."""
    try:
        port = settings.port
        logger.info("🌐 Starting HTTP health server", port=port)
        
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        
        logger.info("✅ HTTP server started successfully", 
                   port=port, 
                   endpoints=["/health", "/status", "/"])
        
        server.serve_forever()
        
    except Exception as e:
        logger.error("❌ HTTP server failed to start", error=str(e), port=settings.port)
        raise


async def main():
    """Main application function."""
    logger.info("🚀 Starting Channel Analytics Bot v2.0...")
    logger.info("Configuration loaded", 
               debug=settings.debug,
               database_configured=bool(settings.database_url),
               admin_users=len(settings.admin_user_ids),
               telemetr_api=bool(settings.telemetr_api_key),
               tgstat_api=bool(settings.tgstat_api_key))
    
    # Start HTTP server in background thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    logger.info("🌐 HTTP health server started in background")
    
    # Check if bot token is configured
    if not settings.bot_token:
        logger.warning("⚠️ BOT_TOKEN not configured - running in health-only mode")
        logger.info("💡 Set BOT_TOKEN environment variable to enable bot functionality")
        logger.info("🏥 Health server is running at /health")
        
        # Keep health server running indefinitely
        try:
            while True:
                await asyncio.sleep(60)  # Sleep for 1 minute
                logger.debug("💓 Health server heartbeat")
        except KeyboardInterrupt:
            logger.info("👋 Health server shutting down")
            return 0
    
    # Validate required configuration for bot functionality
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        logger.error("❌ TELEGRAM_API_ID and TELEGRAM_API_HASH are required for bot")
        logger.info("💡 Get API credentials from https://my.telegram.org/apps")
        logger.info("🏥 Running in health-only mode instead")
        
        # Keep health server running indefinitely
        try:
            while True:
                await asyncio.sleep(60)
                logger.debug("💓 Health server heartbeat")
        except KeyboardInterrupt:
            logger.info("👋 Health server shutting down")
            return 0
    
    if not settings.admin_user_ids:
        logger.warning("⚠️ No admin users configured - bot will have limited functionality")
        logger.info("💡 Set ADMIN_USER_IDS environment variable with comma-separated user IDs")

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("📡 Received shutdown signal", signal=signum)
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Start the bot
        await start_bot()
        
    except KeyboardInterrupt:
        logger.info("👋 Graceful shutdown initiated")
        
    except Exception as e:
        logger.error("❌ Critical error in main application", error=str(e))
        return 1
    
    finally:
        # Cleanup
        try:
            await stop_bot()
            logger.info("✅ Application shutdown completed")
        except Exception as e:
            logger.error("❌ Error during shutdown", error=str(e))
    
    return 0


def validate_environment():
    """Validate environment and dependencies."""
    logger.info("🔍 Validating environment...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        logger.error("❌ Python 3.11+ is required", current_version=sys.version)
        return False
    
    # Check required environment variables
    required_vars = ["BOT_TOKEN", "TELEGRAM_API_ID", "TELEGRAM_API_HASH"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error("❌ Missing required environment variables", missing=missing_vars)
        logger.info("💡 Set these variables in Railway dashboard or .env file")
        return False
    
    # Check database URL format
    if not settings.database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
        logger.error("❌ Invalid database URL format", url=settings.database_url[:20] + "...")
        logger.info("💡 DATABASE_URL should start with postgresql:// or postgresql+asyncpg://")
        return False
    
    # Test imports of critical dependencies
    try:
        import aiogram
        import telethon
        import sqlalchemy
        import matplotlib
        import structlog
        logger.info("✅ All critical dependencies available")
    except ImportError as e:
        logger.error("❌ Missing critical dependency", error=str(e))
        logger.info("💡 Run: pip install -r requirements.txt")
        return False
    
    logger.info("✅ Environment validation passed")
    return True


if __name__ == "__main__":
    # Validate environment first
    if not validate_environment():
        sys.exit(1)
    
    # Run main application
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    
    except KeyboardInterrupt:
        logger.info("👋 Application interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.error("💥 Unhandled exception in main", error=str(e))
        sys.exit(1)
