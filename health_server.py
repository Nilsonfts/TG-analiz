#!/usr/bin/env python3
"""
Простой HTTP сервер для healthcheck и мониторинга
"""
import http.server
import socketserver
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Обработчик GET запросов"""
        if self.path == "/health":
            # Healthcheck endpoint
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "telegram-analytics-bot"}')
            
        elif self.path == "/":
            # Главная страница
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Telegram Channel Analytics Bot</title>
                <meta charset="utf-8">
            </head>
            <body>
                <h1>🚀 Telegram Channel Analytics Bot</h1>
                <p>✅ Сервер работает</p>
                <p>📊 Бот готов к анализу каналов</p>
                <p>🤖 Все системы в норме</p>
                <hr>
                <p><a href="/health">Health Check</a></p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
        else:
            # 404 для остальных путей
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

def start_server():
    """Запуск HTTP сервера"""
    port = int(os.environ.get("PORT", 8000))
    
    try:
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            logger.info(f"🌐 HTTP сервер запущен на порту {port}")
            logger.info(f"📋 Health check: http://localhost:{port}/health")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"❌ Ошибка запуска HTTP сервера: {e}")

if __name__ == "__main__":
    start_server()
