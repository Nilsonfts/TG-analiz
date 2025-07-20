#!/usr/bin/env python3
"""
Супер простой HTTP сервер для Railway
ТОЛЬКО health check - ничего больше
"""
import os
import http.server
import socketserver
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthOnlyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        logger.info(f"Получен запрос: {self.path}")
        
        # Отвечаем OK на любой запрос
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')
        
        logger.info(f"Отправлен ответ 200 OK")
    
    def log_message(self, format, *args):
        logger.info(format % args)

if __name__ == "__main__":
    PORT = int(os.environ.get('PORT', 8000))
    
    logger.info(f"Запуск сервера на порту {PORT}")
    logger.info(f"Переменная PORT из окружения: {os.environ.get('PORT', 'НЕ УСТАНОВЛЕНА')}")
    
    with socketserver.TCPServer(("", PORT), HealthOnlyHandler) as httpd:
        logger.info(f"Сервер слушает на 0.0.0.0:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Сервер остановлен")
