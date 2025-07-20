#!/usr/bin/env python3
"""Minimal Flask health server for Railway"""
import os
import json

try:
    from flask import Flask, jsonify
    app = Flask(__name__)
    
    @app.route('/')
    @app.route('/health')
    def health():
        return jsonify({
            "status": "healthy",
            "service": "railway-bot",
            "port": int(os.getenv("PORT", "8080"))
        })
    
    if __name__ == "__main__":
        port = int(os.getenv("PORT", "8080"))
        print(f"🚀 Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        
except ImportError:
    # Fallback to built-in server
    print("Flask not available, using built-in server")
    
    import http.server
    import socketserver
    
    PORT = int(os.getenv("PORT", "8080"))
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
    
    print(f"Starting simple server on port {PORT}")
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        httpd.serve_forever()
