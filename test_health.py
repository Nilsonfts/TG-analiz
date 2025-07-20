#!/usr/bin/env python3
"""
Test health endpoint locally
"""
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import HealthHandler, PORT

def test_health_endpoint():
    """Test the health endpoint locally"""
    print(f"🧪 Testing health endpoint on port {PORT}")
    
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        print(f"✅ HTTP server started on 0.0.0.0:{PORT}")
        print(f"📊 Test: curl http://localhost:{PORT}/health")
        print(f"📊 Test: curl http://localhost:{PORT}/")
        print("🔥 Press Ctrl+C to stop")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_health_endpoint()
