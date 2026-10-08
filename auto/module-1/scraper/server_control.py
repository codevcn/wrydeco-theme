from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

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
    })
    return record


def unregister_server_process(record: Path) -> None:
    try:
        record.unlink(missing_ok=True)
    except OSError:
        pass


def _windows_process(pid: int) -> dict[str, Any] | None:
    script = (
        f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {pid}\"; "
        "if ($null -eq $p) { exit 3 }; "
        "$p | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"
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
        return executable == expected_executable and "-m scraper serve" in " ".join(command.split())
    command_path = Path("/proc") / str(pid) / "cmdline"
    if not command_path.is_file():
        return False
    command = command_path.read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").casefold()
    return "-m scraper serve" in " ".join(command.split())


def stop_registered_servers(package_root: Path) -> dict[str, list[int]]:
    registry = _registry_dir(package_root)
    stopped: list[int] = []
    stale: list[int] = []
    failed: list[int] = []
    if not registry.is_dir():
        return {"stopped": stopped, "stale": stale, "failed": failed}

    for record_path in sorted(registry.glob("*.json")):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            pid = int(record["pid"])
            if not _registered_process_matches(record):
                stale.append(pid)
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
                os.kill(pid, signal.SIGTERM)
            stopped.append(pid)
            unregister_server_process(record_path)
        except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError, subprocess.TimeoutExpired):
            failed.append(int(record_path.stem) if record_path.stem.isdigit() else -1)
    return {"stopped": stopped, "stale": stale, "failed": failed}
