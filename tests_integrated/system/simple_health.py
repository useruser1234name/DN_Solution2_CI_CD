#!/usr/bin/env python
"""
간단한 헬스체크 서버
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'status': 'ok',
                'message': 'Health check passed'
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # 로그 출력 비활성화
        pass

if __name__ == '__main__':
    port = 8000
    server = HTTPServer(('localhost', port), HealthHandler)
    print(f"Simple health server running on http://localhost:{port}/health/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nServer stopped.")

