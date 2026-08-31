#!/usr/bin/env python3
"""Launch Northstar as a native desktop window.

Starts the local orchestrator, then opens a frameless WKWebView (macOS) /
WebView2 (Windows) / WebKitGTK (Linux) window. Closing the window stops
the process. This is not a browser tab.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UI_INDEX = ROOT / "frontend" / "out" / "index.html"


class WindowBridge:
    """JS-callable window controls for the in-app traffic lights."""

    def __init__(self) -> None:
        self.window = None
        self._zoomed = False

    def close(self) -> None:
        if self.window:
            self.window.destroy()

    def minimize(self) -> None:
        if self.window:
            self.window.minimize()

    def zoom(self) -> None:
        if not self.window:
            return
        if self._zoomed:
            self.window.restore()
            self._zoomed = False
            return
        self.window.maximize()
        self._zoomed = True


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _ensure_ui() -> None:
    if UI_INDEX.exists():
        return
    frontend = ROOT / "frontend"
    npm = "npm"
    print("Building the cockpit (first launch)…", flush=True)
    subprocess.check_call([npm, "install"], cwd=frontend)
    subprocess.check_call([npm, "run", "build"], cwd=frontend)
    if not UI_INDEX.exists():
        raise SystemExit("UI build did not produce frontend/out/index.html")


def _wait_healthy(port: int, timeout_s: float = 20.0) -> None:
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.4) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
        time.sleep(0.12)
    raise SystemExit(f"Orchestrator did not start on port {port}: {last_error}")


def main() -> None:
    try:
        import uvicorn
        import webview
    except ImportError as exc:
        raise SystemExit(
            "Desktop extras missing. Run: python3 -m pip install -r requirements.txt"
        ) from exc

    from bootstrap import main as bootstrap

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    bootstrap()
    _ensure_ui()

    port = _free_port()
    print(f"Northstar orchestrator on http://127.0.0.1:{port}", flush=True)
    config = uvicorn.Config(
        "main:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    _wait_healthy(port)

    bridge = WindowBridge()
    window = webview.create_window(
        title="Northstar",
        url=f"http://127.0.0.1:{port}/",
        width=1440,
        height=900,
        min_size=(1080, 700),
        background_color="#F5F5F7",
        frameless=True,
        easy_drag=False,
        js_api=bridge,
        text_select=True,
    )
    bridge.window = window
    webview.start()
    server.should_exit = True


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
