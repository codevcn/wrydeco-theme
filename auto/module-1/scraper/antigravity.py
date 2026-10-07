from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .io_utils import atomic_write_json, load_env, load_json


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_antigravity_command(env: dict[str, str]) -> list[str] | None:
    raw = env.get("ANTIGRAVITY_COMMAND_JSON", "").strip()
    if not raw:
        return None
    try:
        command = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("ANTIGRAVITY_COMMAND_JSON must be a JSON array of command arguments.") from exc
    if not isinstance(command, list) or not command or not all(isinstance(item, str) and item for item in command):
        raise ValueError("ANTIGRAVITY_COMMAND_JSON must be a non-empty JSON array of strings.")
    return command


class AntigravityConversation:
    """Persistent, serialized Antigravity CLI conversation with SSE-friendly events."""

    def __init__(self, package_root: Path, project_root: Path | None = None):
        self.package_root = package_root.resolve()
        self.project_root = (project_root or self.package_root.parent).resolve()
        self.runtime_root = self.package_root / ".runtime" / "server" / "antigravity"
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.runtime_root / "state.json"
        self.events_path = self.runtime_root / "events.jsonl"
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._turn_lock = threading.Lock()
        self._startup_thread: threading.Thread | None = None
        self._state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        try:
            saved = load_json(self.state_path) if self.state_path.is_file() else {}
        except Exception:
            saved = {}
        return {
            "status": "disconnected",
            "message": "Sẵn sàng khôi phục conversation khi dashboard được mở.",
            "conversation_id": saved.get("conversation_id"),
            "num_turns": saved.get("num_turns", 0),
            "last_event_id": saved.get("last_event_id", 0),
            "updated_at": _utc_now(),
        }

    def _save_state(self) -> None:
        atomic_write_json(self.state_path, self._state)

    def _append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._condition:
            event_id = int(self._state.get("last_event_id", 0)) + 1
            record = {"id": event_id, "at": _utc_now(), **event}
            with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._state["last_event_id"] = event_id
            self._state["updated_at"] = record["at"]
            self._save_state()
            self._condition.notify_all()
            return record

    def _set_status(self, status: str, message: str, **extra: Any) -> None:
        with self._condition:
            self._state.update({"status": status, "message": message, **extra})
            self._append_event({"event": "antigravity_status", "status": status, "message": message})

    def _configuration(self) -> tuple[list[str] | None, str | None]:
        try:
            command = parse_antigravity_command(load_env(self.package_root / ".env"))
        except ValueError as exc:
            return None, str(exc)
        return command, None

    def state(self) -> dict[str, Any]:
        command, error = self._configuration()
        with self._lock:
            return {**self._state, "configured": command is not None, "configuration_error": error}

    def ensure_connected(self, force: bool = False) -> dict[str, Any]:
        with self._lock:
            if self._startup_thread and self._startup_thread.is_alive():
                return self.state()
            if not force and self._state.get("status") in {"connected", "busy"}:
                return self.state()
            command, error = self._configuration()
            if command is None:
                self._set_status("error", error or "Antigravity chưa được cấu hình trong scraper/.env.")
                return self.state()
            self._set_status("connecting", "Đang khởi động persistent conversation với Antigravity…")
            self._startup_thread = threading.Thread(
                target=self._connect_worker,
                daemon=True,
                name="scraper-antigravity-connect",
            )
            self._startup_thread.start()
            return self.state()

    def _connect_worker(self) -> None:
        prompt = (
            "You are the persistent content-authoring agent for this local Amazon-to-Shopify scraper dashboard. "
            "Keep this conversation for future product content tasks. Do not edit files for this initialization turn. "
            "Reply with exactly ANTIGRAVITY_READY."
        )
        try:
            timeout = int(load_env(self.package_root / ".env").get("ANTIGRAVITY_TIMEOUT_SECONDS", "3600"))
            self.run_turn(prompt, timeout=timeout, purpose="connection", connecting=True)
        except Exception as exc:
            self._set_status("error", f"Không thể khởi tạo Antigravity: {exc}")

    def _build_command(self, prompt: str) -> list[str]:
        command, error = self._configuration()
        if command is None:
            raise ValueError(error or "Antigravity is not configured.")
        # Migrate the short-lived bridge configuration used by older dashboard builds.
        if "scraper.antigravity_bridge" in command:
            command = ["agy"]
        argv = list(command)
        argv.extend(["--input-format", "text", "--output-format", "stream-json", "--mode", "accept-edits"])
        conversation_id = self._state.get("conversation_id")
        if conversation_id:
            argv.extend(["--conversation", str(conversation_id)])
        argv.append(f"--print={prompt}")
        return argv

    def run_turn(
        self,
        prompt: str,
        *,
        timeout: int,
        purpose: str,
        connecting: bool = False,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        with self._turn_lock:
            status = "connecting" if connecting else "busy"
            message = "Đang kết nối Antigravity…" if connecting else f"Antigravity đang xử lý: {purpose}"
            self._set_status(status, message)
            try:
                command = self._build_command(prompt)
            except ValueError as exc:
                self._set_status("error", str(exc))
                return False, "not_configured"

            child_env = os.environ.copy()
            child_env.update({"SCRAPER_PHASE": "content"})
            child_env.update(extra_env or {})
            try:
                process = subprocess.Popen(
                    command,
                    cwd=self.project_root,
                    env=child_env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    shell=False,
                    bufsize=1,
                )
            except OSError as exc:
                self._set_status("error", f"Không thể khởi động Antigravity: {exc}")
                return False, "launch_failed"

            messages: queue.Queue[tuple[str, str | None]] = queue.Queue()

            def reader(name: str, stream: Any) -> None:
                for line in iter(stream.readline, ""):
                    messages.put((name, line.rstrip()))
                messages.put((name, None))

            for stream_name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
                threading.Thread(target=reader, args=(stream_name, stream), daemon=True).start()

            deadline = time.monotonic() + timeout
            next_heartbeat = time.monotonic() + 15
            closed: set[str] = set()
            result_status: str | None = None
            while process.poll() is None or len(closed) < 2:
                now = time.monotonic()
                if now >= deadline and process.poll() is None:
                    process.kill()
                    event = {"event": "agent_error", "purpose": purpose, "message": "Antigravity timed out."}
                    self._append_event(event)
                    if event_callback:
                        event_callback(event)
                    self._set_status("error", "Antigravity timed out.")
                    return False, "timeout"
                if now >= next_heartbeat and process.poll() is None:
                    elapsed = max(1, timeout - int(deadline - now))
                    event = {"event": "agent_heartbeat", "purpose": purpose,
                             "message": f"Antigravity vẫn đang chạy · {elapsed}s"}
                    self._append_event(event)
                    if event_callback:
                        event_callback(event)
                    next_heartbeat = now + 15
                try:
                    stream_name, line = messages.get(timeout=0.2)
                except queue.Empty:
                    continue
                if line is None:
                    closed.add(stream_name)
                    continue
                event = {"event": "agent_log", "purpose": purpose, "stream": stream_name, "message": line}
                self._append_event(event)
                if event_callback:
                    event_callback(event)
                if stream_name != "stdout":
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                conversation_id = payload.get("conversation_id")
                if not conversation_id and isinstance(payload.get("result"), dict):
                    conversation_id = payload["result"].get("conversation_id")
                    result_status = payload["result"].get("status")
                    self._state["num_turns"] = payload["result"].get("num_turns", self._state.get("num_turns", 0))
                if conversation_id:
                    with self._lock:
                        self._state["conversation_id"] = conversation_id
                        self._save_state()

            return_code = process.wait()
            if return_code != 0 or result_status != "SUCCESS" or not self._state.get("conversation_id"):
                if return_code != 0:
                    reason = f"exit_{return_code}"
                elif result_status != "SUCCESS":
                    reason = f"result_{result_status or 'missing'}"
                else:
                    reason = "conversation_id_missing"
                self._set_status("error", f"Antigravity thất bại: {reason}.")
                return False, reason
            conversation_id = self._state.get("conversation_id")
            suffix = f" · {str(conversation_id)[:8]}" if conversation_id else ""
            self._set_status("connected", f"Đã kết nối persistent conversation{suffix}.")
            return True, "ok"

    def events_after(self, event_id: int) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        output = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if int(event.get("id", 0)) > event_id:
                output.append(event)
        return output

    def wait_for_change(self, timeout: float = 15.0) -> None:
        with self._condition:
            self._condition.wait(timeout=timeout)
