import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlparse, parse_qs
import time
import threading
import random
import argparse

# Simuler l'état du Nerf gun
nerf_status = "idle"
last_check_time = time.time()

def check_ko_state():
    global nerf_status, last_check_time
    current_time = time.time()
    if current_time - last_check_time >= 600:  # 10 minutes
        if random.random() < 0.05:  # 5% chance
            nerf_status = "ko"
        last_check_time = current_time

class NerfHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        check_ko_state()
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/nerf":
            self.handle_nerf(parse_qs(parsed_path.query))
        elif parsed_path.path == "/stop":
            self.handle_stop()
        elif parsed_path.path == "/status":
            self.handle_status()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        check_ko_state()
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        parsed_data = parse_qs(post_data.decode('utf-8'))

        if self.path == "/nerf":
            self.handle_nerf(parsed_data)
        else:
            self.send_error(404, "Not Found")

    def handle_nerf(self, params):
        global nerf_status
        if nerf_status == "ko":
            self.send_error(503, "Service Unavailable")
            return
        elif nerf_status == "busy":
            self.send_error(429, "Too Many Requests")
            return
        
        nerf_status = "busy"
        
        x = params.get('x', [0])[0]
        y = params.get('y', [0])[0]
        shot = int(params.get('shot', [1])[0])
        
        response = f"Nerf activated: x={x}, y={y}, shot={shot}"
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(response.encode())
        
        # Simulate the time taken for shots
        threading.Thread(target=self.simulate_shots, args=(shot,)).start()

    def simulate_shots(self, shots):
        global nerf_status
        time.sleep(0.5 * shots)
        nerf_status = "idle"

    def handle_stop(self):
        global nerf_status
        nerf_status = "idle"
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write("Nerf stopped".encode())

    def handle_status(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        status_json = json.dumps({"status": nerf_status})
        self.wfile.write(status_json.encode())

def run(port):
    server_address = ('', port)
    httpd = HTTPServer(server_address, NerfHandler)
    print(f"Starting Nerf server on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Nerf Gun Control Server")
    parser.add_argument('-p', '--port', type=int, default=5555, help="Port to run the server on (default: 5555)")
    args = parser.parse_args()

    run(args.port)
    