#!/usr/bin/env python3
"""
Минимальный HTTP сервер только для healthcheck
"""
import os
import http.server
import socketserver
import json
from datetime import datetime

class MinimalHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Отключаем логи
        
    def do_GET(self):
        if self.path in ["/", "/health", "/healthz"]:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "ok", "timestamp": datetime.now().isoformat()}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    with socketserver.TCPServer(("", port), MinimalHandler) as httpd:
        print(f"Server running on port {port}")
        httpd.serve_forever()
