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
        # Включаем базовое логирование для диагностики
        print(f"📡 HTTP {format % args}")
    
    def do_GET(self):
        print(f"🔍 Health check request: {self.path}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        response = {
            "status": "healthy",
            "service": "tg-analytics-bot", 
            "version": "2.0.0",
            "port": PORT,
            "path": self.path,
            "message": "Railway health check OK"
        }
        self.wfile.write(json.dumps(response, indent=2).encode())

def run_server():
    try:
        print(f"🌐 Binding to 0.0.0.0:{PORT}")
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        print(f"✅ Health server started successfully!")
        print(f"🏥 Health endpoint: http://0.0.0.0:{PORT}/")
        print(f"🏥 Alternative: http://0.0.0.0:{PORT}/health")
        print(f"📡 Listening for Railway health checks...")
        
        server.serve_forever()
        
    except OSError as e:
        print(f"❌ Port {PORT} binding error: {e}")
        print(f"💡 Railway may need a different port")
        return 1
    except Exception as e:
        print(f"❌ Server error: {e}")
        return 1

if __name__ == "__main__":
    print(f"🚀 Starting Railway health server on port {PORT}")
    run_server()
