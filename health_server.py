#!/usr/bin/env python3
"""
RAILWAY HEALTH CHECK - MINIMAL VERSION
Простейший HTTP сервер для Railway health check
"""
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.getenv("PORT", "8080"))

class HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Отключаем логи HTTP сервера
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        response = {"status": "ok", "healthy": True, "service": "tg-bot"}
        self.wfile.write(json.dumps(response).encode())

def run_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        print(f"✅ Health server running on port {PORT}")
        print(f"🏥 Health check: http://0.0.0.0:{PORT}/")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    run_server()
