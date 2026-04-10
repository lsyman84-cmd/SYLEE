#!/usr/bin/env python3
"""Simple launcher for the weather PWA static files."""

from __future__ import annotations

import argparse
import os
import socket
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class NoCacheRequestHandler(SimpleHTTPRequestHandler):
    """Disable browser caching to avoid stale service-worker assets."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def detect_lan_ip() -> str:
    """Best-effort LAN IP detection for same-Wi-Fi phone access."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run weather app static server.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", default=8080, type=int, help="Bind port (default: 8080)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)

    httpd = ThreadingHTTPServer((args.host, args.port), NoCacheRequestHandler)
    lan_ip = detect_lan_ip()

    print(f"날씨 앱 서버 실행 중: http://localhost:{args.port}")
    if args.host in ("0.0.0.0", "::"):
        print(f"휴대폰 접속 주소: http://{lan_ip}:{args.port}")
    print("종료하려면 Ctrl+C를 누르세요.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("\n서버를 종료했습니다.")


if __name__ == "__main__":
    main()
