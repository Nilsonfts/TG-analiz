#!/usr/bin/env python3
"""
Flask minimal server for deployment
"""
import os

try:
    from flask import Flask
    
    app = Flask(__name__)
    
    @app.route('/')
    @app.route('/health')
    @app.route('/healthz')
    def health():
        return 'OK', 200
    
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 8000))
        app.run(host='0.0.0.0', port=port, debug=False)

except ImportError:
    # Fallback to basic HTTP server if Flask not available
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class HealthHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass
        
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
    
    if __name__ == '__main__':
        port = int(os.environ.get('PORT', 8000))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        server.serve_forever()
