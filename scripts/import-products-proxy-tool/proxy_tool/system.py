from __future__ import annotations

import ctypes
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import REPORT_DIR, STATE_DIR, ensure_runtime_dirs


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION,
        False,
        pid,
    )

    if handle:
        ctypes.windll.kernel32.CloseHandle(handle)
        return True

    return False


def terminate_pid(pid: int) -> bool:
    if not pid_alive(pid):
        return True

    PROCESS_TERMINATE = 0x0001

    handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_TERMINATE,
        False,
        pid,
    )

    if not handle:
        return False

    try:
        return bool(ctypes.windll.kernel32.TerminateProcess(handle, 1))
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def powershell(script: str, timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def process_command_line(pid: int) -> str:
    safe_pid = int(pid)

    proc = powershell(
        f"""
        $p = Get-CimInstance Win32_Process -Filter "ProcessId={safe_pid}" `
             -ErrorAction SilentlyContinue
        if ($p) {{ $p.CommandLine }}
        """
    )

    return (proc.stdout or "").strip()


def terminate_if_ours(pid: int, signature: str) -> bool:
    command_line = process_command_line(pid)

    if not command_line:
        return not pid_alive(pid)

    if signature.lower() not in command_line.lower():
        return False

    return terminate_pid(pid)


def snapshot_connections() -> list[dict]:
    proc = powershell(
        r"""
        $processMap = @{}
        Get-Process -ErrorAction SilentlyContinue | ForEach-Object {
            $processMap[$_.Id] = $_.ProcessName
        }

        $rows = Get-NetTCPConnection -ErrorAction SilentlyContinue |
            Select-Object `
                LocalAddress,
                LocalPort,
                RemoteAddress,
                RemotePort,
                State,
                OwningProcess,
                @{Name='ProcessName';Expression={$processMap[$_.OwningProcess]}}

        if ($rows) {
            $rows | ConvertTo-Json -Depth 4 -Compress
        } else {
            '[]'
        }
        """
    )

    if proc.returncode != 0:
        return []

    text = (proc.stdout or "").strip()

    if not text:
        return []

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []

    if isinstance(parsed, dict):
        return [parsed]

    return parsed


def connection_key(row: dict) -> tuple:
    return (
        str(row.get("LocalAddress", "")),
        int(row.get("LocalPort", 0) or 0),
        str(row.get("RemoteAddress", "")),
        int(row.get("RemotePort", 0) or 0),
        int(row.get("OwningProcess", 0) or 0),
    )


def write_network_snapshot(name: str) -> Path:
    ensure_runtime_dirs()

    path = REPORT_DIR / f"{name}.network.json"

    proc = powershell(
        r"""
        Get-NetIPConfiguration |
            Select-Object `
                InterfaceAlias,
                InterfaceIndex,
                IPv4Address,
                IPv6Address,
                IPv4DefaultGateway,
                IPv6DefaultGateway,
                DNSServer |
            ConvertTo-Json -Depth 8
        """
    )

    payload = {
        "captured_at": time.time(),
        "returncode": proc.returncode,
        "data": proc.stdout.strip() if proc.returncode == 0 else None,
    }

    atomic_json(path, payload)
    return path


class RedactingFilter(logging.Filter):
    def __init__(self, secrets: list[str]):
        super().__init__()
        self.secrets = sorted(
            {x for x in secrets if x},
            key=len,
            reverse=True,
        )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        for secret in self.secrets:
            message = message.replace(secret, "[REDACTED]")

        record.msg = message
        record.args = ()
        return True


def get_logger(name: str, secrets: list[str]) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
    )
    handler.addFilter(RedactingFilter(secrets))

    logger.addHandler(handler)
    logger.propagate = False

    return logger


class PacketMonitor:
    """
    Captures only deliberately generated leak probes.

    It intentionally does NOT capture the upstream proxy endpoint,
    so proxy credentials cannot end up inside the capture.
    """

    PROBE_IPS = [
        "1.1.1.1",
        "8.8.8.8",
        "2606:4700:4700::1111",
    ]

    def __init__(self, prefix: str):
        ensure_runtime_dirs()
        self.etl = REPORT_DIR / f"{prefix}.pktmon.etl"
        self.pcap = REPORT_DIR / f"{prefix}.pktmon.pcapng"
        self.started = False

    @staticmethod
    def _run(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["pktmon.exe", *args],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def start(self) -> None:
        status = self._run(["status"])

        # We own filters/capture only when no previous capture is active.
        status_text = (
            (status.stdout or "") + "\n" + (status.stderr or "")
        ).lower()

        if "running" in status_text:
            raise RuntimeError(
                "pktmon is already running. "
                "Refusing to interfere with another packet capture."
            )

        self._run(["filter", "remove"])

        for index, ip in enumerate(self.PROBE_IPS, start=1):
            result = self._run(
                [
                    "filter",
                    "add",
                    f"ProxyGateProbe{index}",
                    "-i",
                    ip,
                ]
            )

            if result.returncode != 0:
                self._run(["filter", "remove"])
                raise RuntimeError(
                    f"Unable to configure pktmon probe filter for {ip}."
                )

        self.etl.unlink(missing_ok=True)
        self.pcap.unlink(missing_ok=True)

        result = self._run(
            [
                "start",
                "--capture",
                "--pkt-size",
                "96",
                "--file-name",
                str(self.etl),
                "--file-size",
                "32",
                "--log-mode",
                "circular",
            ]
        )

        if result.returncode != 0:
            self._run(["filter", "remove"])
            raise RuntimeError(
                "pktmon could not start packet capture."
            )

        self.started = True

    def stop(self) -> None:
        if self.started:
            self._run(["stop"])
            self.started = False

            if self.etl.exists():
                self._run(
                    [
                        "etl2pcap",
                        str(self.etl),
                        "--out",
                        str(self.pcap),
                    ]
                )

        self._run(["filter", "remove"])


def cleanup_pktmon() -> None:
    try:
        subprocess.run(
            ["pktmon.exe", "stop"],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        pass

    try:
        subprocess.run(
            ["pktmon.exe", "filter", "remove"],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        pass


def runtime_file() -> Path:
    return STATE_DIR / "runtime.json"