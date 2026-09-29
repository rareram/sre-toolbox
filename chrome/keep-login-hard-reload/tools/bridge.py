#!/usr/bin/env python3
"""
KeepLogin Hard Reload - Cross-Platform Local Agent Bridge
Works out-of-the-box on macOS, Linux, and Windows with standard Python 3 (no pip packages required).

Usage:
  1. Start Bridge Server (runs on 127.0.0.1:8765):
     python3 bridge.py --server

  2. Trigger Reload from Agent, CLI, or Build Watcher:
     python3 bridge.py --trigger
     # OR with curl:
     curl -X POST http://127.0.0.1:8765/reload
     # OR target a specific origin:
     curl -X POST "http://127.0.0.1:8765/reload?origin=http://localhost:3000"
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from queue import Queue, Empty

PORT = 8765
HOST = "127.0.0.1"

# Event queue for long-polling / SSE clients (Chrome Extension)
event_queue = Queue()


class BridgeRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        # Health check
        if parsed.path == "/health":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "app": "KeepLogin Hard Reload Bridge"}')
            return

        # Poll endpoint for Chrome Extension (Long-polling)
        if parsed.path == "/events":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            try:
                # Wait up to 25 seconds for a reload trigger
                event = event_queue.get(timeout=25)
                self.wfile.write(json.dumps(event).encode("utf-8"))
            except Empty:
                # Timeout, return heartbeat
                self.wfile.write(b'{"command": "heartbeat"}')
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/reload":
            query = urllib.parse.parse_qs(parsed.query)
            target_origin = query.get("origin", [None])[0]

            payload = {
                "command": "hard_reload",
                "target_origin": target_origin,
                "timestamp": int(time.time() * 1000)
            }

            event_queue.put(payload)
            target_info = f" ({target_origin})" if target_origin else " (active tab)"
            print(f"[Bridge] Triggered reload request{target_info}")

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": "Reload event queued"}).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress verbose default request logs except error/reload
        if "reload" in self.path or "health" in self.path:
            super().log_message(format, *args)


def run_server(port=PORT):
    server_address = (HOST, port)
    httpd = HTTPServer(server_address, BridgeRequestHandler)
    print(f"============================================================")
    print(f" KeepLogin Hard Reload - Local Agent Bridge Server")
    print(f" Listening on http://{HOST}:{port}")
    print(f" - Extension poll endpoint: http://{HOST}:{port}/events")
    print(f" - Reload trigger endpoint: POST http://{HOST}:{port}/reload")
    print(f" Compatible with macOS, Linux, and Windows (Python 3 native)")
    print(f" Press Ctrl+C to terminate.")
    print(f"============================================================")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Bridge] Server stopped.")
        httpd.server_close()


def send_trigger(origin=None, port=PORT):
    url = f"http://{HOST}:{port}/reload"
    if origin:
        url += f"?origin={urllib.parse.quote(origin)}"

    req = urllib.request.Request(url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[Success] Trigger sent: {data}")
    except Exception as e:
        print(f"[Error] Failed to connect to bridge at {url}: {e}")
        print("Ensure 'python3 bridge.py --server' is running in the background.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Cross-platform Local Bridge for KeepLogin Hard Reload")
    parser.add_argument("--server", action="store_true", help="Start local bridge server")
    parser.add_argument("--trigger", action="store_true", help="Send reload trigger to browser")
    parser.add_argument("--origin", type=str, default=None, help="Optional target origin (e.g. http://localhost:3000)")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port number (default: {PORT})")

    args = parser.parse_args()

    if args.trigger:
        send_trigger(args.origin, args.port)
    else:
        # Default to server mode
        run_server(args.port)


if __name__ == "__main__":
    main()
