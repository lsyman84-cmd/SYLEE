"""
날씨 Streamlit 앱 실행 스크립트.

사용법 (프로젝트 폴더에서):
  .\\.venv\\Scripts\\python run.py
  .\\.venv\\Scripts\\python run.py --tunnel   # 휴대폰 LTE 등 외부 접속 (localhost.run)

옵션:
  --port 8501
  --tunnel   SSH 역방향 터널로 https 주소 출력 (OpenSSH 클라이언트 필요)
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
STREAMLIT_APP = ROOT / "streamlit_app.py"


def pick_python() -> Path:
    if VENV_PY.is_file():
        return VENV_PY
    return Path(sys.executable)


def wait_http_ok(url: str, timeout: float = 30.0) -> bool:
    try:
        import urllib.request
    except ImportError:
        time.sleep(5)
        return True
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except OSError:
            time.sleep(0.5)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Streamlit 날씨 앱 실행")
    parser.add_argument("--port", type=int, default=int(os.getenv("STREAMLIT_PORT", "8501")))
    parser.add_argument(
        "--address",
        default=os.getenv("STREAMLIT_ADDRESS", "0.0.0.0"),
        help="Streamlit bind 주소 (기본 0.0.0.0: 같은 Wi‑Fi에서 접속)",
    )
    parser.add_argument(
        "--tunnel",
        action="store_true",
        help="localhost.run SSH 터널로 외부 https URL 생성",
    )
    args = parser.parse_args()

    if not STREAMLIT_APP.is_file():
        print(f"streamlit_app.py 없음: {STREAMLIT_APP}", file=sys.stderr)
        return 1

    py = pick_python()
    cmd = [
        str(py),
        "-m",
        "streamlit",
        "run",
        str(STREAMLIT_APP),
        "--server.port",
        str(args.port),
        "--server.address",
        args.address,
        "--server.headless",
        "true",
    ]

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")

    print("실행:", " ".join(cmd))
    st_proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    def pump_streamlit_out() -> None:
        assert st_proc.stdout is not None
        for line in st_proc.stdout:
            print(line, end="")

    threading.Thread(target=pump_streamlit_out, daemon=True).start()

    local_url = f"http://127.0.0.1:{args.port}"
    if not wait_http_ok(local_url):
        print("Streamlit이 뜨는 데 시간이 걸립니다. 브라우저에서 직접 열어보세요:", local_url)

    print(f"\n로컬: {local_url}")
    if args.address == "0.0.0.0":
        print("같은 네트워크: 이 PC의 LAN IP와 포트로 접속 (예: http://192.168.x.x:{args.port})")

    tunnel_proc: subprocess.Popen[str] | None = None
    if args.tunnel:
        ssh_cmd = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-R",
            f"80:127.0.0.1:{args.port}",
            "nokey@localhost.run",
        ]
        print("\n터널:", " ".join(ssh_cmd))
        tunnel_proc = subprocess.Popen(
            ssh_cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert tunnel_proc.stdout is not None
        url_re = re.compile(r"https://[a-zA-Z0-9.-]+\.lhr\.life")
        for _ in range(200):
            line = tunnel_proc.stdout.readline()
            if not line:
                break
            print(line, end="")
            m = url_re.search(line)
            if m:
                print(f"\n>>> 외부 접속 URL: {m.group(0)}\n")
                break

    def shutdown(_sig=None, _frame=None) -> None:
        if tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        if st_proc.poll() is None:
            st_proc.terminate()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    try:
        st_proc.wait()
    except KeyboardInterrupt:
        shutdown()
    finally:
        shutdown()

    return st_proc.returncode or 0


if __name__ == "__main__":
    raise SystemExit(main())
