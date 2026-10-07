from __future__ import annotations

import asyncio
import json
import os
import queue
import secrets
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from .antigravity import AntigravityConversation, parse_antigravity_command
from .config import PACKAGE_ROOT, Settings
from .content import validate_content
from .errors import ContentValidationError, ManifestError
from .io_utils import atomic_write_json, atomic_write_text, load_env, load_json
from .manifest import Manifest, load_manifest, parse_manifest_payload
from .pipeline import Pipeline


TERMINAL_JOB_STATUSES = {"applied", "completed", "failed", "needs_attention", "waiting_for_agent", "interrupted"}
ACTIVE_JOB_STATUSES = {"queued", "running", "agent_running"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_run_options(payload: Any) -> dict[str, Any]:
    raw = payload if isinstance(payload, dict) else {}
    try:
        maximum = int(raw.get("max_combinations", 100))
    except (TypeError, ValueError) as exc:
        raise ValueError("max_combinations must be an integer.") from exc
    if not 1 <= maximum <= 100:
        raise ValueError("max_combinations must be between 1 and 100.")
    postal = str(raw.get("amazon_postal_code", "10001")).strip()
    if not postal.isdigit() or len(postal) not in {5, 9}:
        raise ValueError("amazon_postal_code must contain 5 or 9 digits.")
    return {
        "headless": bool(raw.get("headless", True)),
        "dry_run": bool(raw.get("dry_run", False)),
        "max_combinations": maximum,
        "amazon_postal_code": postal,
    }


class DashboardJobManager:
    def __init__(self, package_root: Path = PACKAGE_ROOT,
                 pipeline_runner: Callable[[Manifest, Settings, bool, Callable[[dict[str, Any]], None]], dict[str, Any]] | None = None):
        self.package_root = package_root.resolve()
        self.project_root = self.package_root.parent
        self.runtime_root = self.package_root / ".runtime" / "server" / "jobs"
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.pipeline_runner = pipeline_runner or self._default_pipeline_runner
        self.antigravity: AntigravityConversation | None = None
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._threads: dict[str, threading.Thread] = {}
        self._mark_interrupted_jobs()

    @staticmethod
    def _default_pipeline_runner(manifest: Manifest, settings: Settings, dry_run: bool,
                                 callback: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        return asyncio.run(Pipeline(manifest, settings, dry_run=dry_run, event_callback=callback).run())

    def _job_dir(self, job_id: str) -> Path:
        if not job_id or any(character not in "0123456789abcdef" for character in job_id):
            raise KeyError(job_id)
        return self.runtime_root / job_id

    def _metadata_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "job.json"

    def _events_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "events.jsonl"

    def _load(self, job_id: str) -> dict[str, Any]:
        path = self._metadata_path(job_id)
        if not path.is_file():
            raise KeyError(job_id)
        return load_json(path)

    def _save(self, job: dict[str, Any]) -> None:
        job["updated_at"] = utc_now()
        atomic_write_json(self._metadata_path(job["id"]), job)

    def _mark_interrupted_jobs(self) -> None:
        for path in self.runtime_root.glob("*/job.json"):
            try:
                job = load_json(path)
                if job.get("status") in ACTIVE_JOB_STATUSES:
                    job["status"] = "interrupted"
                    job["message"] = "Server restarted while this job was active. Resume is safe from checkpoints."
                    job["updated_at"] = utc_now()
                    atomic_write_json(path, job)
            except Exception:
                continue

    def _active_job(self) -> dict[str, Any] | None:
        for path in self.runtime_root.glob("*/job.json"):
            try:
                job = load_json(path)
            except Exception:
                continue
            thread = self._threads.get(str(job.get("id", "")))
            if job.get("status") in ACTIVE_JOB_STATUSES and thread and thread.is_alive():
                return job
        return None

    def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        jobs = []
        for path in self.runtime_root.glob("*/job.json"):
            try:
                jobs.append(load_json(path))
            except Exception:
                continue
        jobs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return jobs[:limit]

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            return self._load(job_id)

    def record_event(self, job_id: str, event: dict[str, Any]) -> dict[str, Any]:
        return self._append_event(job_id, event)

    def start(self, manifest: Manifest, prompt: str, options: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            active = self._active_job()
            if active:
                raise RuntimeError(f"Job {active['id']} is already running.")
            job_id = uuid.uuid4().hex
            execution_dir = self.package_root / "runs" / manifest.digest / "_server" / job_id
            execution_dir.mkdir(parents=True, exist_ok=True)
            prompt_path = execution_dir / "agent_prompt.md"
            atomic_write_text(prompt_path, prompt.rstrip() + "\n")
            job = {
                "id": job_id,
                "run_id": manifest.digest,
                "status": "queued",
                "message": "Queued",
                "manifest_path": str(manifest.path),
                "prompt_path": str(prompt_path),
                "execution_dir": str(execution_dir),
                "options": options,
                "products": {item.asin: {"status": "pending", "amazon_url": item.amazon_url,
                                           "shopify_product_id": item.shopify_product_id} for item in manifest.products},
                "summary": None,
                "last_event_id": 0,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            self._job_dir(job_id).mkdir(parents=True, exist_ok=True)
            self._save(job)
            self._append_event(job_id, {"event": "job_created", "message": "Manifest validated; job queued."})
            self._launch(job_id)
            return self._load(job_id)

    def resume(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            active = self._active_job()
            if active:
                raise RuntimeError(f"Job {active['id']} is already running.")
            job = self._load(job_id)
            if job.get("status") not in TERMINAL_JOB_STATUSES:
                raise RuntimeError("Only a stopped job can be resumed.")
            waiting = (job.get("summary") or {}).get("waiting_for_content") or []
            missing_content = [
                asin for asin in waiting
                if not (self.package_root / "runs" / job["run_id"] / asin / "content.json").is_file()
            ]
            if job.get("status") == "waiting_for_agent" and missing_content:
                try:
                    agent_command = parse_antigravity_command(load_env(self.package_root / ".env"))
                except ValueError as exc:
                    raise RuntimeError(f"Antigravity configuration is invalid: {exc}") from exc
                if agent_command is None:
                    asin_list = ", ".join(missing_content)
                    raise RuntimeError(
                        "Antigravity chưa được cấu hình và content.json vẫn còn thiếu cho "
                        f"{asin_list}. Cấu hình ANTIGRAVITY_COMMAND_JSON hoặc tạo content.json trước khi Resume."
                    )
            job["status"] = "queued"
            job["message"] = "Resume queued"
            job["resume_count"] = int(job.get("resume_count", 0)) + 1
            self._save(job)
            self._append_event(job_id, {"event": "job_resumed", "message": "Resuming from saved checkpoints."})
            self._launch(job_id)
            return self._load(job_id)

    def _launch(self, job_id: str) -> None:
        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True,
                                  name=f"scraper-dashboard-{job_id[:8]}")
        self._threads[job_id] = thread
        thread.start()

    def _append_event(self, job_id: str, event: dict[str, Any]) -> dict[str, Any]:
        with self._condition:
            job = self._load(job_id)
            event_id = int(job.get("last_event_id", 0)) + 1
            record = {"id": event_id, "at": utc_now(), **event}
            path = self._events_path(job_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            job["last_event_id"] = event_id
            if record.get("event") == "product_status" and record.get("asin") in job.get("products", {}):
                product = job["products"][record["asin"]]
                product["status"] = record.get("status", product.get("status"))
                for key in ("error", "error_type", "stage", "current", "total"):
                    if key in record:
                        product[key] = record[key]
            elif record.get("asin") in job.get("products", {}):
                product = job["products"][record["asin"]]
                for key in ("stage", "current", "total", "price", "kind"):
                    if key in record:
                        product[key] = record[key]
            self._save(job)
            self._condition.notify_all()
            return record

    def events_after(self, job_id: str, event_id: int) -> list[dict[str, Any]]:
        self._load(job_id)
        path = self._events_path(job_id)
        if not path.exists():
            return []
        output = []
        for line in path.read_text(encoding="utf-8").splitlines():
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

    def _set_status(self, job_id: str, status: str, message: str, **extra: Any) -> None:
        # Persist the terminal event and terminal status as one critical section.
        # Otherwise an SSE reader can observe a terminal status with the previous
        # last_event_id and close just before the final status event is appended.
        with self._condition:
            job = self._load(job_id)
            job.update({"status": status, "message": message, **extra})
            event_id = int(job.get("last_event_id", 0)) + 1
            record = {"id": event_id, "at": utc_now(), "event": "job_status",
                      "status": status, "message": message}
            path = self._events_path(job_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            job["last_event_id"] = event_id
            self._save(job)
            self._condition.notify_all()

    def _event_callback(self, job_id: str) -> Callable[[dict[str, Any]], None]:
        def callback(event: dict[str, Any]) -> None:
            self._append_event(job_id, event)
        return callback

    def _run_pipeline(self, job_id: str) -> dict[str, Any]:
        job = self._load(job_id)
        manifest = load_manifest(Path(job["manifest_path"]))
        options = job["options"]
        settings = Settings(
            env_path=self.package_root / ".env",
            headless=bool(options["headless"]),
            max_combinations=int(options["max_combinations"]),
            amazon_postal_code=str(options["amazon_postal_code"]),
        )
        return self.pipeline_runner(manifest, settings, bool(options["dry_run"]), self._event_callback(job_id))

    @staticmethod
    def _content_failures(summary: dict[str, Any]) -> list[dict[str, Any]]:
        return [item for item in summary.get("failed", []) if item.get("error_type") == "ContentValidationError"]

    def _agent_context(self, job: dict[str, Any], summary: dict[str, Any], attempt: int) -> str:
        waiting = summary.get("waiting_for_content", [])
        failures = self._content_failures(summary)
        return (
            "\n\n---\n"
            "SERVER EXECUTION CONTEXT (authoritative):\n"
            "The local dashboard already ran the scraper. Do not run the scraper and do not mutate Shopify.\n"
            f"Run ID: {job['run_id']}\n"
            f"Run directory: {self.package_root / 'runs' / job['run_id']}\n"
            f"Content-authoring attempt: {attempt}/3\n"
            f"Waiting ASINs: {json.dumps(waiting, ensure_ascii=False)}\n"
            f"Validation errors to fix: {json.dumps(failures, ensure_ascii=False)}\n"
            "Write only the required content.json files, then exit successfully.\n"
        )

    def _run_agent(self, job_id: str, summary: dict[str, Any], attempt: int) -> tuple[bool, str]:
        job = self._load(job_id)
        env_values = load_env(self.package_root / ".env")
        command = parse_antigravity_command(env_values)
        if command is None:
            return False, "not_configured"
        timeout = int(env_values.get("ANTIGRAVITY_TIMEOUT_SECONDS", "3600"))
        prompt = Path(job["prompt_path"]).read_text(encoding="utf-8") + self._agent_context(job, summary, attempt)
        log_path = Path(job["execution_dir"]) / "agent.log"
        self._set_status(job_id, "agent_running", f"Antigravity content attempt {attempt}/3")
        if self.antigravity is not None:
            with log_path.open("a", encoding="utf-8", newline="\n") as log:
                def persist_agent_event(event: dict[str, Any]) -> None:
                    message = str(event.get("message", ""))
                    log.write(f"[{event.get('stream', event.get('event', 'agent'))}] {message}\n")
                    log.flush()

                return self.antigravity.run_turn(
                    prompt,
                    timeout=timeout,
                    purpose=f"content attempt {attempt}/3 · run {job['run_id']}",
                    event_callback=persist_agent_event,
                    extra_env={
                        "SCRAPER_MANIFEST": str(job["manifest_path"]),
                        "SCRAPER_RUN_ID": str(job["run_id"]),
                        "SCRAPER_RUN_DIR": str(self.package_root / "runs" / job["run_id"]),
                        "SCRAPER_PHASE": "content",
                    },
                )
        child_env = os.environ.copy()
        child_env.update({
            "SCRAPER_MANIFEST": str(job["manifest_path"]),
            "SCRAPER_RUN_ID": str(job["run_id"]),
            "SCRAPER_RUN_DIR": str(self.package_root / "runs" / job["run_id"]),
            "SCRAPER_PHASE": "content",
        })
        process = subprocess.Popen(
            command, cwd=self.project_root, env=child_env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
            errors="replace", shell=False, bufsize=1,
        )
        assert process.stdin is not None
        process.stdin.write(prompt)
        process.stdin.close()
        messages: queue.Queue[tuple[str, str | None]] = queue.Queue()

        def reader(name: str, stream: Any) -> None:
            for line in iter(stream.readline, ""):
                messages.put((name, line.rstrip()))
            messages.put((name, None))

        readers = []
        for stream_name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            thread = threading.Thread(target=reader, args=(stream_name, stream), daemon=True)
            thread.start()
            readers.append(thread)
        deadline = time.monotonic() + timeout
        next_heartbeat = time.monotonic() + 15
        closed = set()
        with log_path.open("a", encoding="utf-8", newline="\n") as log:
            while process.poll() is None or len(closed) < 2:
                if time.monotonic() >= deadline and process.poll() is None:
                    process.kill()
                    self._append_event(job_id, {"event": "agent_error", "message": "Antigravity timed out."})
                    return False, "timeout"
                if time.monotonic() >= next_heartbeat and process.poll() is None:
                    elapsed = max(1, timeout - int(deadline - time.monotonic()))
                    self._append_event(job_id, {
                        "event": "agent_heartbeat",
                        "message": f"Antigravity vẫn đang chạy · {elapsed}s",
                    })
                    next_heartbeat = time.monotonic() + 15
                try:
                    stream_name, line = messages.get(timeout=0.2)
                except queue.Empty:
                    continue
                if line is None:
                    closed.add(stream_name)
                    continue
                log.write(f"[{stream_name}] {line}\n")
                log.flush()
                self._append_event(job_id, {"event": "agent_log", "stream": stream_name, "message": line})
        return_code = process.wait()
        if return_code != 0:
            return False, f"exit_{return_code}"
        return True, "ok"

    def _finish_from_summary(self, job_id: str, summary: dict[str, Any]) -> None:
        job = self._load(job_id)
        with self._lock:
            job["summary"] = summary
            self._save(job)
        if summary.get("needs_attention"):
            self._set_status(job_id, "needs_attention", "At least one product needs attention.")
        elif summary.get("failed"):
            self._set_status(job_id, "failed", "At least one product failed.")
        elif job["options"].get("dry_run"):
            self._set_status(job_id, "completed", "Dry run completed without Shopify mutations.")
        else:
            self._set_status(job_id, "applied", "Batch completed and Shopify is synchronized.")

    def _run_job(self, job_id: str) -> None:
        try:
            self._set_status(job_id, "running", "Running scraper pipeline.")
            summary = self._run_pipeline(job_id)
            for attempt in range(1, 4):
                needs_content = bool(summary.get("waiting_for_content") or self._content_failures(summary))
                if not needs_content:
                    self._finish_from_summary(job_id, summary)
                    return
                try:
                    agent_ok, reason = self._run_agent(job_id, summary, attempt)
                except (OSError, ValueError) as exc:
                    self._set_status(job_id, "needs_attention", f"Antigravity configuration failed: {exc}")
                    return
                if reason == "not_configured":
                    with self._lock:
                        job = self._load(job_id)
                        job["summary"] = summary
                        self._save(job)
                    self._set_status(job_id, "waiting_for_agent",
                                     "Crawl complete. Copy the prompt, create content.json, then Resume.")
                    return
                if not agent_ok:
                    self._set_status(job_id, "needs_attention", f"Antigravity failed: {reason}.")
                    return
                self._set_status(job_id, "running", "Validating Agent content and continuing pipeline.")
                summary = self._run_pipeline(job_id)
            self._finish_from_summary(job_id, summary)
        except Exception as exc:
            self._append_event(job_id, {"event": "server_error", "message": str(exc),
                                        "error_type": type(exc).__name__})
            self._set_status(job_id, "failed", f"Dashboard worker failed: {exc}")


def create_app(package_root: Path = PACKAGE_ROOT, manager: DashboardJobManager | None = None) -> Flask:
    package_root = package_root.resolve()
    app = Flask(
        __name__,
        template_folder=str(package_root / "web" / "templates"),
        static_folder=str(package_root / "web" / "static"),
        static_url_path="/static",
    )
    app.config.update(JSON_SORT_KEYS=False)
    app.extensions["dashboard_manager"] = manager or DashboardJobManager(package_root)
    app.extensions["antigravity_conversation"] = AntigravityConversation(package_root)
    app.extensions["dashboard_manager"].antigravity = app.extensions["antigravity_conversation"]
    app.extensions["dashboard_csrf"] = secrets.token_urlsafe(32)

    def job_manager() -> DashboardJobManager:
        return app.extensions["dashboard_manager"]

    def antigravity() -> AntigravityConversation:
        return app.extensions["antigravity_conversation"]

    def manifest_path() -> Path:
        return package_root / "input" / "products.json"

    def save_manifest(payload: Any) -> Manifest:
        manifest = parse_manifest_payload(payload, manifest_path())
        atomic_write_json(manifest_path(), payload)
        return manifest

    @app.before_request
    def protect_mutations() -> Response | None:
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        expected_origin = request.host_url.rstrip("/")
        origin = request.headers.get("Origin", "")
        token = request.headers.get("X-CSRF-Token", "")
        if origin != expected_origin or not secrets.compare_digest(token, app.extensions["dashboard_csrf"]):
            return jsonify({"error": "Invalid Origin or CSRF token."}), 403
        if request.mimetype != "application/json":
            return jsonify({"error": "Mutating requests require application/json."}), 415
        return None

    @app.errorhandler(ManifestError)
    @app.errorhandler(ContentValidationError)
    @app.errorhandler(ValueError)
    def bad_request(exc: Exception) -> tuple[Response, int]:
        return jsonify({"error": str(exc)}), 400

    @app.errorhandler(KeyError)
    def not_found(_: KeyError) -> tuple[Response, int]:
        return jsonify({"error": "Job was not found."}), 404

    @app.get("/")
    def index() -> str:
        antigravity().ensure_connected()
        return render_template("index.html")

    @app.get("/api/bootstrap")
    def bootstrap() -> Response:
        target = manifest_path()
        if not target.exists():
            target = package_root / "input" / "products.example.json"
        manifest_payload = load_json(target) if target.exists() else {"products": []}
        prompt_path = package_root / "AGENT_PROMPT.md"
        return jsonify({
            "manifest": manifest_payload,
            "prompt": prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else "",
            "defaults": {"headless": True, "dry_run": False, "amazon_postal_code": "10001",
                         "max_combinations": 100},
            "csrf_token": app.extensions["dashboard_csrf"],
            "jobs": job_manager().list_jobs(),
            "agent": antigravity().state(),
        })

    @app.get("/api/antigravity")
    def antigravity_status() -> Response:
        return jsonify(antigravity().state())

    @app.post("/api/antigravity/connect")
    def antigravity_connect() -> tuple[Response, int]:
        return jsonify(antigravity().ensure_connected(force=True)), 202

    @app.get("/api/antigravity/events")
    def antigravity_events() -> Response:
        try:
            cursor = int(request.headers.get("Last-Event-ID") or request.args.get("after") or 0)
        except ValueError:
            cursor = 0

        @stream_with_context
        def generate():
            nonlocal cursor
            while True:
                events = antigravity().events_after(cursor)
                for event in events:
                    cursor = int(event["id"])
                    yield f"id: {cursor}\nevent: antigravity\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                if not events:
                    yield ": heartbeat\n\n"
                    antigravity().wait_for_change(10.0)

        return Response(generate(), mimetype="text/event-stream", headers={
            "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
        })

    @app.put("/api/manifest")
    def update_manifest() -> Response:
        manifest = save_manifest(request.get_json(force=False, silent=False))
        return jsonify({"ok": True, "run_id": manifest.digest, "products": len(manifest.products)})

    @app.post("/api/runs")
    def start_run() -> tuple[Response, int]:
        payload = request.get_json(force=False, silent=False) or {}
        manifest_payload = payload.get("manifest")
        manifest = save_manifest(manifest_payload)
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("Prompt cannot be empty.")
        options = validate_run_options(payload.get("options"))
        try:
            job = job_manager().start(manifest, prompt, options)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(job), 202

    @app.get("/api/runs")
    def list_runs() -> Response:
        return jsonify({"jobs": job_manager().list_jobs()})

    @app.get("/api/runs/<job_id>")
    def get_run(job_id: str) -> Response:
        return jsonify(job_manager().get(job_id))

    def content_path_for(job_id: str, asin: str) -> tuple[dict[str, Any], Path]:
        job = job_manager().get(job_id)
        if asin not in job.get("products", {}):
            raise KeyError(asin)
        return job, package_root / "runs" / job["run_id"] / asin / "content.json"

    @app.get("/api/runs/<job_id>/products/<asin>/content")
    def get_product_content(job_id: str, asin: str) -> Response:
        job, content_path = content_path_for(job_id, asin)
        payload = load_json(content_path) if content_path.is_file() else {}
        validation_error = None
        if payload:
            try:
                validate_content(payload)
            except ContentValidationError as exc:
                validation_error = str(exc)
        return jsonify({
            "job_id": job_id,
            "run_id": job["run_id"],
            "asin": asin,
            "exists": content_path.is_file(),
            "content": payload,
            "valid": bool(payload) and validation_error is None,
            "validation_error": validation_error,
        })

    @app.put("/api/runs/<job_id>/products/<asin>/content")
    def update_product_content(job_id: str, asin: str) -> Response:
        job, content_path = content_path_for(job_id, asin)
        payload = request.get_json(force=False, silent=False)
        if not isinstance(payload, dict):
            raise ValueError("content.json must contain a JSON object.")
        normalized = validate_content(payload)
        atomic_write_json(content_path, payload)
        job_manager().record_event(job_id, {
            "event": "content_saved",
            "asin": asin,
            "message": "content.json đã được validate và lưu atomic.",
        })
        return jsonify({
            "ok": True,
            "job_id": job_id,
            "run_id": job["run_id"],
            "asin": asin,
            "valid": True,
            "content": payload,
            "normalized": normalized,
        })

    @app.post("/api/runs/<job_id>/resume")
    def resume_run(job_id: str) -> tuple[Response, int]:
        try:
            job = job_manager().resume(job_id)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify(job), 202

    @app.get("/api/runs/<job_id>/events")
    def stream_events(job_id: str) -> Response:
        job_manager().get(job_id)
        try:
            cursor = int(request.headers.get("Last-Event-ID") or request.args.get("after") or 0)
        except ValueError:
            cursor = 0

        @stream_with_context
        def generate():
            nonlocal cursor
            while True:
                events = job_manager().events_after(job_id, cursor)
                for event in events:
                    cursor = int(event["id"])
                    yield f"id: {cursor}\nevent: progress\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                job = job_manager().get(job_id)
                if job.get("status") in TERMINAL_JOB_STATUSES and cursor >= int(job.get("last_event_id", 0)):
                    return
                if not events:
                    yield ": heartbeat\n\n"
                    job_manager().wait_for_change(10.0)

        return Response(generate(), mimetype="text/event-stream", headers={
            "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
        })

    return app


def serve(host: str = "127.0.0.1", port: int = 5000) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("The scraper dashboard only binds to a loopback address.")
    create_app().run(host=host, port=port, threaded=True, use_reloader=False)
