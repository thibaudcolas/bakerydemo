"""
Simple HTTP server that adds the Service-Worker-Allowed header so the
service worker at /wasm/worker.js can control the root scope (/).
"""

import http.server
import os
import sys


class WasmHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Service-Worker-Allowed", "/")
        super().end_headers()

    def do_GET(self):
        # Serve wasm/index.html for the root path
        if self.path == "/" or self.path == "/index.html":
            self.path = "/wasm/index.html"
        return super().do_GET()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 1337
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    server = http.server.HTTPServer(("", port), WasmHTTPRequestHandler)
    print(f"Serving WASM playground at http://localhost:{port}")
    print(f"Open http://localhost:{port} to start")
    print("Press Ctrl+C to stop")
    server.serve_forever()
