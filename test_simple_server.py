#!/usr/bin/env python3
"""
Простой тест HTTP сервера для Railway health checks
"""
import http.server
import socketserver
import os
import threading
import time

def test_health_server():
    """Тест простого HTTP сервера"""
    port = int(os.getenv('PORT', 8000))
    
    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK')
            elif self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Telegram Analytics Bot is running')
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            # Подавляем логи HTTP сервера
            pass

    def run_server():
        with socketserver.TCPServer(('', port), HealthHandler) as httpd:
            print(f"HTTP сервер запущен на порту {port}")
            httpd.serve_forever()
    
    # Запуск сервера в отдельном потоке
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    return server_thread

if __name__ == "__main__":
    print("Запуск тестового HTTP сервера...")
    test_health_server()
    
    # Небольшая задержка для запуска сервера
    time.sleep(1)
    
    # Тест endpoints
    import requests
    try:
        response = requests.get('http://localhost:8000/health')
        print(f"Health check: {response.status_code} - {response.text}")
        
        response = requests.get('http://localhost:8000/')
        print(f"Root endpoint: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Ошибка при тестировании: {e}")
    
    # Держим сервер запущенным
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nСервер остановлен")
