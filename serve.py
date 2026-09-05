"""Single-origin static + reverse-proxy server for the SIH-26154 demo.

Serves the React frontend on :8080 and forwards /sources/*, /jobs/* to the
FastAPI backend on :8000. This means the public Cloudflare URL has no CORS
issues — frontend and API share an origin.
"""
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib import request, error

BACKEND = os.getenv("BACKEND", "http://127.0.0.1:8000")
FRONTEND_DIR = os.getenv("FRONTEND_DIR", os.path.join(os.path.dirname(__file__), "frontend"))
PORT = int(os.getenv("PORT", "8080"))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/sources") or self.path.startswith("/jobs") or self.path.startswith("/openapi.json"):
            return self._proxy("GET")
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/sources") or self.path.startswith("/jobs"):
            return self._proxy("POST")
        return super().do_POST()

    def _proxy(self, method: str):
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else None
        url = BACKEND + self.path
        req = request.Request(url, data=body, method=method)
        ct = self.headers.get("Content-Type")
        if ct:
            req.add_header("Content-Type", ct)
        try:
            with request.urlopen(req, timeout=120) as resp:
                payload = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
        except error.HTTPError as e:
            payload = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as e:
            msg = ('{"error":"%s"}' % str(e)).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)


if __name__ == "__main__":
    print(f"Serving {FRONTEND_DIR} on http://127.0.0.1:{PORT}, proxying to {BACKEND}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()