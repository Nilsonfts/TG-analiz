#!/usr/bin/env python3
"""
Minimal Railway Telegram Bot with working health check
"""
import asyncio
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8080"))

class SimpleHealthHandler(BaseHTTPRequestHandler):
    """Simple health check handler"""
    
    def log_message(self, format, *args):
        """Suppress HTTP logs"""
        pass
    
    def do_GET(self):
        """Handle GET requests"""
        logger.info(f"Health check request: {self.path}")
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        if self.path == '/health':
            response = {
                "status": "ok",
                "healthy": True,
                "service": "telegram-bot",
                "port": PORT,
                "bot_configured": bool(BOT_TOKEN)
            }
        else:
            response = {
                "message": "TG-analiz Bot",
                "status": "running",
                "health_endpoint": "/health"
            }
        
        response_json = json.dumps(response, indent=2)
        self.wfile.write(response_json.encode('utf-8'))
        logger.info(f"Response sent: {response}")

def run_health_server():
    """Run health check server"""
    try:
        logger.info(f"🏥 Starting health server on 0.0.0.0:{PORT}")
        server = HTTPServer(('0.0.0.0', PORT), SimpleHealthHandler)
        logger.info(f"✅ Health server ready at http://0.0.0.0:{PORT}/health")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Health server error: {e}")
        raise

async def run_telegram_bot():
    """Run Telegram bot if token is available"""
    if not BOT_TOKEN:
        logger.warning("⚠️ BOT_TOKEN not set - bot features disabled")
        return
    
    try:
        from telegram.ext import Application, CommandHandler
        from telegram import Update
        
        logger.info("🤖 Starting Telegram bot...")
        
        async def start_command(update: Update, context):
            await update.message.reply_text(
                "🚀 TG-analiz Bot is running on Railway!\n\n"
                "✅ Health check: /health\n"
                "📊 Status: Operational"
            )
        
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start_command))
        
        logger.info("✅ Telegram bot configured")
        await app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Telegram bot error: {e}")

async def main():
    """Main application"""
    logger.info("🚀 TG-analiz starting...")
    logger.info(f"🔧 Port: {PORT}")
    logger.info(f"🤖 Bot token: {'✅' if BOT_TOKEN else '❌'}")
    
    # Start health server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Give server time to start
    await asyncio.sleep(2)
    logger.info("🏥 Health check server started")
    
    # Run telegram bot (or keep alive if no token)
    if BOT_TOKEN:
        await run_telegram_bot()
    else:
        logger.info("🔄 Keeping service alive for health checks...")
        try:
            while True:
                await asyncio.sleep(60)
                logger.info("💓 Service heartbeat")
        except KeyboardInterrupt:
            logger.info("👋 Graceful shutdown")

if __name__ == "__main__":
    asyncio.run(main())
