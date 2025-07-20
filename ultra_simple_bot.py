#!/usr/bin/env python3
"""Ultra simple health server for Railway"""
import http.server
import socketserver
import json
import os

PORT = int(os.getenv("PORT", "8080"))

class SimpleHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "healthy", 
            "service": "railway-bot",
            "port": PORT
        }
        self.wfile.write(json.dumps(response).encode())
        
    def log_message(self, format, *args):
        print(f"LOG: {format % args}")

if __name__ == "__main__":
    print(f"Starting server on port {PORT}")
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), SimpleHandler) as httpd:
            print(f"Server running at http://0.0.0.0:{PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"ERROR: {e}")
        # Try localhost instead
        try:
            with socketserver.TCPServer(("127.0.0.1", PORT), SimpleHandler) as httpd:
                print(f"Server running at http://127.0.0.1:{PORT}")
                httpd.serve_forever()
        except Exception as e2:
            print(f"FAILED: {e2}")
