#!/usr/bin/env python3
"""
Ультра-простой health server для Railway
БЕЗ ЗАВИСИМОСТЕЙ - только стандартная библиотека Python
"""
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "railway-health"}')
            logger.info("Health check successful")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Переопределяем для контроля логирования
        logger.info(format % args)

def main():
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"🚀 Starting Railway Health Server on port {port}")
    
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    
    try:
        logger.info(f"✅ Server ready at http://0.0.0.0:{port}")
        logger.info("📊 Health endpoint: /health")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped")
        server.shutdown()

if __name__ == '__main__':
    main()
