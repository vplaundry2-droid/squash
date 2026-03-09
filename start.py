from __future__ import annotations

import http.server
import socketserver
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8000


def main() -> None:
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Serving Squash Sim at http://localhost:{PORT}")
        print("Press Ctrl-C to stop.")
        try:
            webbrowser.open(f"http://localhost:{PORT}")
        except Exception:
            pass
        httpd.serve_forever()


if __name__ == "__main__":
    main()
