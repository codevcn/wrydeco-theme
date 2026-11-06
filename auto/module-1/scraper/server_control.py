from __future__ import annotations

import json
import os
import secrets
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .io_utils import atomic_write_json


def _registry_dir(package_root: Path) -> Path:
    return package_root / ".runtime" / "servers"


def register_server_process(package_root: Path, host: str, port: int) -> Path:
    registry = _registry_dir(package_root)
    registry.mkdir(parents=True, exist_ok=True)
    record = registry / f"{os.getpid()}.json"
    atomic_write_json(record, {
        "pid": os.getpid(),
        "host": host,
        "port": int(port),
        "started_at": time.time(),
        "executable": str(Path(sys.executable).resolve()),
        "shutdown_protocol": 1,
        "shutdown_token": secrets.token_urlsafe(24),
    })
    return record


def unregister_server_process(record: Path) -> None:
    for path in (record, record.with_suffix(".stop")):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def server_stop_requested(record: Path) -> bool:
    try:
        registered = json.loads(record.read_text(encoding="utf-8"))
        requested = json.loads(record.with_suffix(".stop").read_text(encoding="utf-8"))
        token = registered.get("shutdown_token")
        return isinstance(token, str) and bool(token) and requested.get("token") == token
    except (OSError, ValueError, AttributeError):
        return False


class ServerStopController:
    """Combine console keys, process signals and the workspace stop command."""
    def __init__(self, record: Path, *, key_reader: Callable[[], str | None] | None = None):
        self.record = record
        self.event = threading.Event()
        self._signals: dict[int, Any] = {}
        self._thread: threading.Thread | None = None
        self._key_reader = key_reader
        self._console_mode = None
        self._native_console = self._key_reader is None and os.name == "nt" and sys.stdin and sys.stdin.isatty()
        if self._native_console:
            import msvcrt
            self._key_reader = lambda: msvcrt.getwch() if msvcrt.kbhit() else None

    def _capture_console_ctrl_c(self):
        if not self._native_console:
            return
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel.GetStdHandle.restype = wintypes.HANDLE
        kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetConsoleMode.restype = wintypes.BOOL
        kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.SetConsoleMode.restype = wintypes.BOOL
        handle = kernel.GetStdHandle(-10)  # STD_INPUT_HANDLE
        original = wintypes.DWORD()
        if kernel.GetConsoleMode(handle, ctypes.byref(original)):
            # Receive Ctrl+C as a key, so CMD does not also interrupt the batch file
            # and ask "Terminate batch job (Y/N)?" after Python has cleaned up.
            if kernel.SetConsoleMode(handle, original.value & ~0x0001):  # ENABLE_PROCESSED_INPUT
                self._console_mode = (kernel, handle, original.value)

    def _restore_console_mode(self):
        saved, self._console_mode = self._console_mode, None
        if saved:
            kernel, handle, mode = saved
            kernel.SetConsoleMode(handle, mode)

    def request_stop(self, *_args) -> None:
        self.event.set()

    def requested(self) -> bool:
        if not self.event.is_set() and server_stop_requested(self.record):
            self.request_stop()
        return self.event.is_set()

    def _read_keys(self) -> None:
        extended = False
        while not self.event.wait(.05):
            try:
                key = self._key_reader()
            except (OSError, EOFError):
                self._restore_console_mode()
                return
            if key is None:
                continue
            if extended:
                extended = False
            elif key in {"\x00", "\xe0"}:
                extended = True
            elif key.lower() == "q" or key == "\x03":
                self.request_stop()

    def __enter__(self):
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM):
                self._signals[sig] = signal.signal(sig, self.request_stop)
        if self._key_reader:
            self._capture_console_ctrl_c()
            self._thread = threading.Thread(target=self._read_keys, daemon=True, name="scraper-console-stop")
            self._thread.start()
        return self

    def __exit__(self, *_args):
        self.request_stop()
        if self._thread:
            self._thread.join(timeout=.5)
        self._restore_console_mode()
        for sig, previous in self._signals.items():
            signal.signal(sig, previous)


def _windows_process(pid: int) -> dict[str, Any] | None:
    script = (
        f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\"; "
        "if ($null -eq $p) { exit 3 }; "
        "$p | Select-Object ProcessId,ExecutablePath,CommandLine,"
        "@{Name='StartedAt';Expression={($_.CreationDate.ToUniversalTime()-[datetime]'1970-01-01').TotalSeconds}} "
        "| ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=False,
    )
    if result.returncode == 3 or not result.stdout.strip():
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Unable to inspect PID {pid}.")
    return json.loads(result.stdout)


def _registered_process_matches(record: dict[str, Any]) -> bool:
    pid = int(record["pid"])
    expected_executable = str(Path(record.get("executable") or "").resolve()).casefold()
    if os.name == "nt":
        process = _windows_process(pid)
        if process is None:
            return False
        command = str(process.get("CommandLine") or "").casefold()
        executable = str(Path(process.get("ExecutablePath") or "").resolve()).casefold()
        reused_pid = float(process.get("StartedAt") or 0) > float(record.get("started_at") or 0)
        return not reused_pid and executable == expected_executable and "-m scraper serve" in " ".join(command.split())
    command_path = Path("/proc") / str(pid) / "cmdline"
    if not command_path.is_file():
        return False
    command = command_path.read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").casefold()
    return "-m scraper serve" in " ".join(command.split())


def stop_registered_servers(package_root: Path, *, grace_seconds: float = 30) -> dict[str, list[int]]:
    registry = _registry_dir(package_root)
    stopped: list[int] = []
    stale: list[int] = []
    failed: list[int] = []
    forced: list[int] = []
    if not registry.is_dir():
        return {"stopped": stopped, "stale": stale, "failed": failed, "forced": forced}

    for record_path in sorted(registry.glob("*.json")):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            pid = int(record["pid"])
            if not _registered_process_matches(record):
                stale.append(pid)
                unregister_server_process(record_path)
                continue
            if record.get("shutdown_protocol") == 1 and record.get("shutdown_token"):
                atomic_write_json(record_path.with_suffix(".stop"), {"token": record["shutdown_token"]})
                deadline = time.monotonic() + grace_seconds
                while record_path.exists() and time.monotonic() < deadline:
                    time.sleep(.1)
                if not record_path.exists():
                    stopped.append(pid)
                    continue
                # A new registration at the same PID must not be terminated or removed.
                if json.loads(record_path.read_text(encoding="utf-8")) != record:
                    stopped.append(pid)
                    continue
            if not _registered_process_matches(record):
                stopped.append(pid)
                unregister_server_process(record_path)
                continue
            if os.name == "nt":
                result = subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                    check=False,
                )
                if result.returncode != 0 and _windows_process(pid) is not None:
                    failed.append(pid)
                    continue
            else:
                os.kill(pid, signal.SIGKILL)
            forced.append(pid)
            stopped.append(pid)
            unregister_server_process(record_path)
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError, subprocess.TimeoutExpired):
            failed.append(int(record_path.stem) if record_path.stem.isdigit() else -1)
    return {"stopped": stopped, "stale": stale, "failed": failed, "forced": forced}
