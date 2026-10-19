"""
Server Process Wrapper (`server_wrapper.py`) for Multi-Store Blog Automation Tool.

Features:
  1. Wraps the HTTP server in a managed child process (`subprocess.Popen`).
  2. Verifies server startup via HTTP readiness probe (`/api/stores` -> HTTP 200).
  3. Automatically opens a browser tab (`webbrowser.open_new_tab`) to the tool URL
     once the server has started successfully.
  4. Listens for the `'q'` (or `'Q'`) key from the user (both instant keypress via
     `msvcrt` on Windows console and `sys.stdin` stream) to cleanly stop the server
     process and exit.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Callable, Optional

import requests

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MODULE_DIR = Path(__file__).resolve().parent


def wait_for_server_ready(
    url: str,
    proc: Optional[subprocess.Popen] = None,
    timeout_sec: float = 15.0,
    poll_interval: float = 0.15,
) -> bool:
    """Poll the server health endpoint until HTTP 200 is returned or timeout expires."""
    deadline = time.time() + timeout_sec
    health_url = f"{url.rstrip('/')}/api/stores"
    if proc is not None:
        time.sleep(0.25)
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            return False
        try:
            resp = requests.get(health_url, timeout=1.5)
            if resp.status_code == 200:
                if proc is not None and proc.poll() is not None:
                    return False
                return True
        except Exception:
            pass
        time.sleep(poll_interval)
    return False


def open_tool_browser_tab(url: str) -> bool:
    """Open a new browser tab pointing to `url`."""
    try:
        opened = webbrowser.open_new_tab(url)
        if opened:
            return True
    except Exception:
        pass

    if os.name == "nt":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        except Exception:
            pass
    return False


def _start_stdin_quit_listener(stop_event: threading.Event) -> None:
    """Background listener that sets `stop_event` when 'q' is received via stdin."""

    def _reader() -> None:
        try:
            while not stop_event.is_set():
                ch = sys.stdin.read(1)
                if not ch:
                    break
                if ch.lower() == "q":
                    stop_event.set()
                    break
        except Exception:
            pass

    t = threading.Thread(target=_reader, daemon=True)
    t.start()


def _poll_windows_console_quit_key(stop_event: threading.Event) -> None:
    """Poll `msvcrt.kbhit()` on Windows console for instant 'q' keypress without Enter."""
    if os.name != "nt":
        return
    try:
        import msvcrt

        while not stop_event.is_set():
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch and ch.lower() == "q":
                    stop_event.set()
                    break
            time.sleep(0.08)
    except Exception:
        pass


def terminate_server_process(proc: subprocess.Popen, timeout_sec: float = 5.0) -> None:
    """Cleanly terminate the wrapped child server process."""
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.wait(timeout=2.0)
        except Exception:
            pass
    except Exception:
        pass


def _kill_existing_port_owners(port: int) -> None:
    """Ensure no stale server process is still bound to `port` on Windows (SO_REUSEADDR shadowing)."""
    if os.name != "nt":
        return
    try:
        my_pid = os.getpid()
        ps_cmd = (
            f"Get-NetTCPConnection -LocalPort {int(port)} -State Listen -ErrorAction SilentlyContinue "
            f"| Select-Object -ExpandProperty OwningProcess -Unique"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in (res.stdout or "").splitlines():
            line = line.strip()
            if line.isdigit():
                pid = int(line)
                if pid > 0 and pid != my_pid:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                        timeout=5,
                    )
    except Exception:
        pass


def run_wrapped_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    browser_opener: Optional[Callable[[str], bool]] = None,
) -> int:
    """
    Launch the server child process, wait until ready, open a browser tab,
    and block until the user presses 'q' (or Ctrl+C) to stop the server.
    """
    _kill_existing_port_owners(port)
    cli_script = MODULE_DIR / "cli.py"
    cmd = [
        sys.executable,
        str(cli_script),
        "serve",
        "--raw-server",
        "--host",
        host,
        "--port",
        str(port),
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(MODULE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    url = f"http://{host}:{port}/"
    ready = wait_for_server_ready(url, proc=proc, timeout_sec=15.0)
    if not ready:
        out_text = ""
        if proc.stdout:
            try:
                out_text = proc.stdout.read()
            except Exception:
                pass
        terminate_server_process(proc)
        print(f"[Wrapper] ERROR: Server failed to start on {url}.\n{out_text}", file=sys.stderr, flush=True)
        return 1

    print("=" * 68, flush=True)
    print(f"  Multi-Store Blog Automation Tool (Atlassian UI) is RUNNING", flush=True)
    print(f"  -> Workspace Board : {url}", flush=True)
    print(f"  -> Store Settings  : {url}settings", flush=True)
    print(f"  -> Server PID      : {proc.pid}", flush=True)
    print("-" * 68, flush=True)
    print("  [Wrapper] Nhấn phím 'q' (hoặc Ctrl+C) để dừng Server và thoát.", flush=True)
    print("=" * 68, flush=True)

    if open_browser:
        opener = browser_opener or open_tool_browser_tab
        opened = opener(url)
        print(f"[Wrapper] Browser tab opened: {url} (status={opened})", flush=True)

    # Continuously drain child stdout/stderr pipe so OS pipe buffer never fills and blocks HTTP handlers
    if proc.stdout:
        def _drain_child_stdout() -> None:
            try:
                for line in proc.stdout:  # type: ignore[union-attr]
                    pass
            except Exception:
                pass

        threading.Thread(target=_drain_child_stdout, daemon=True).start()

    stop_event = threading.Event()
    _start_stdin_quit_listener(stop_event)

    if os.name == "nt":
        win_thread = threading.Thread(
            target=_poll_windows_console_quit_key,
            args=(stop_event,),
            daemon=True,
        )
        win_thread.start()

    try:
        while not stop_event.is_set():
            if proc.poll() is not None:
                print(f"[Wrapper] Server process exited unexpectedly (code={proc.returncode}).", flush=True)
                return proc.returncode or 1
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[Wrapper] Nhận tín hiệu Ctrl+C — Đang dừng Server...", flush=True)
    else:
        print("\n[Wrapper] Đã nhận phím 'q' từ người dùng — Đang dừng Server...", flush=True)
    finally:
        stop_event.set()
        terminate_server_process(proc)
        print("[Wrapper] Server đã dừng hoàn toàn.", flush=True)

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wrapper khởi chạy Server, tự mở tab trình duyệt và lắng nghe phím 'q' để dừng Server."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open a browser tab")
    args = parser.parse_args()

    code = run_wrapped_server(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
