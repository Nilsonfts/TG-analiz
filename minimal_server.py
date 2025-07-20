#!/usr/bin/env python3
"""
Минимальный HTTP сервер для Railway health checks
Только HTTP сервер, без Telegram бота
"""
import http.server
import socketserver
import os
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MinimalHealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        logger.info(f"Запрос: {self.path} от {self.client_address}")
        
        if self.path in ['/health', '/']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(b'OK')
            logger.info(f"Ответ 200 OK для {self.path}")
        else:
            self.send_response(404)
            self.send_header('Connection', 'close')
            self.end_headers()
            logger.info(f"Ответ 404 для {self.path}")
    
    def log_message(self, format, *args):
        logger.info(f"HTTP: {format % args}")

def main():
    port = int(os.getenv('PORT', 8000))
    
    try:
        with socketserver.TCPServer(('0.0.0.0', port), MinimalHealthHandler) as httpd:
            httpd.allow_reuse_address = True
            logger.info(f"Минимальный HTTP сервер запущен на 0.0.0.0:{port}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"Ошибка запуска сервера: {e}")
        raise

if __name__ == "__main__":
    main()
