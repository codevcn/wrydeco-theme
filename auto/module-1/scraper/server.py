from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import threading
import time
import webbrowser
from html import escape
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from markdown_it import MarkdownIt
from werkzeug.serving import make_server

from .config import PACKAGE_ROOT
from .errors import ContentValidationError, ManifestError
from .io_utils import atomic_write_json, atomic_write_text, load_json
from .manifest import parse_manifest_payload
from .orchestrator import RunCoordinator
from .server_control import register_server_process, unregister_server_process
from .store import ClaimError, OrchestratorStore, QueueConflict


DOC_EXTENSIONS = {".md", ".txt"}
PROMPT_FILES = {
    "agent_prompt": "AGENT_PROMPT.md",
    "content_task_prompt": "CONTENT_TASK_PROMPT.md",
}
MAX_PROMPT_BYTES = 256 * 1024
PRODUCT_TYPES_FILE = "product_types.json"
DOC_MARKDOWN = MarkdownIt(
    "commonmark",
    {
        "html": False,
        "linkify": False,
        "typographer": False,
    },
).enable(["table", "strikethrough"])


def _dashboard_url(host: str, port: int) -> str:
    browser_host = host
    if host in {"0.0.0.0", "::", "[::]"}:
        browser_host = "127.0.0.1"
    if ":" in browser_host and not browser_host.startswith("["):
        browser_host = f"[{browser_host}]"
    return f"http://{browser_host}:{port}"


def _open_dashboard(url: str) -> None:
    try:
        webbrowser.open_new_tab(url)
    except Exception:
        # Browser launch is a convenience; it must never bring down the server.
        pass


def _open_antigravity_cleanup_terminal(
    project_root: Path,
    conversation_id: str,
    *,
    executable: str = "agy",
) -> int:
    """Open a visible, targeted Antigravity TUI for user-confirmed deletion."""
    resolved = shutil.which(executable) or executable
    if os.name != "nt":
        raise RuntimeError("Opening the Antigravity cleanup terminal is currently supported on Windows only.")

    def quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    command = (
        f"Set-Location -LiteralPath {quote(str(project_root.resolve()))}; "
        "Write-Host ''; "
        "Write-Host 'Conversation can xoa:' -ForegroundColor Yellow; "
        f"Write-Host {quote(conversation_id)} -ForegroundColor Cyan; "
        "Write-Host 'Trong Antigravity: go /resume, tim dung ID, nhan Ctrl+Delete va xac nhan.'; "
        f"& {quote(str(resolved))}"
    )
    process = subprocess.Popen(
        ["powershell.exe", "-NoLogo", "-NoExit", "-Command", command],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        close_fds=True,
    )
    return int(process.pid)


def _resolve_doc_path(docs_root: Path, raw_path: str) -> Path:
    if not raw_path or Path(raw_path).suffix.lower() not in DOC_EXTENSIONS:
        raise ValueError("Only .md and .txt documentation files are supported.")
    root = docs_root.resolve()
    candidate = (root / raw_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Documentation path is outside scraper/docs.") from exc
    if not candidate.is_file():
        raise KeyError(raw_path)
    return candidate


def _list_docs(docs_root: Path) -> list[dict[str, Any]]:
    if not docs_root.is_dir():
        return []
    root = docs_root.resolve()
    documents: list[dict[str, Any]] = []
    for item in root.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in DOC_EXTENSIONS:
            continue
        resolved = item.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            continue
        documents.append({
            "path": relative.as_posix(),
            "name": relative.name,
            "extension": resolved.suffix.lower(),
            "size": resolved.stat().st_size,
        })
    return sorted(documents, key=lambda item: item["path"].casefold())


def _render_doc_content(extension: str, content: str) -> tuple[str, str]:
    """Render local docs without allowing source HTML to execute in the dashboard."""
    if extension.lower() == ".md":
        return "markdown", DOC_MARKDOWN.render(content)
    return "text", f'<pre class="docs-plain-text">{escape(content)}</pre>'


def _read_prompts(package_root: Path) -> dict[str, Any]:
    prompts: dict[str, str] = {}
    files: dict[str, str] = {}
    for key, filename in PROMPT_FILES.items():
        path = package_root / filename
        prompts[key] = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
        files[key] = filename
    return {"prompts": prompts, "files": files}


def _read_product_types(package_root: Path) -> list[str]:
    payload = load_json(package_root / PRODUCT_TYPES_FILE)
    values = payload.get("product_types") if isinstance(payload, dict) else None
    if not isinstance(values, list):
        raise ValueError(f"{PRODUCT_TYPES_FILE} must contain a product_types array.")
    product_types: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        product_types.append(value)
    return product_types


def _validate_prompts(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Request must contain both prompt strings.")
    source = payload.get("prompts", payload)
    if not isinstance(source, dict):
        raise ValueError("prompts must be an object.")
    validated: dict[str, str] = {}
    for key, filename in PROMPT_FILES.items():
        value = source.get(key)
        if not isinstance(value, str):
            raise ValueError(f"{filename} must be a string.")
        value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not value:
            raise ValueError(f"{filename} cannot be empty.")
        if len(value.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise ValueError(f"{filename} exceeds the 256 KiB limit.")
        validated[key] = value + "\n"
    return validated


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


def _manifest_payload(body: Any) -> dict[str, Any]:
    if isinstance(body, dict) and isinstance(body.get("manifest"), dict):
        return body["manifest"]
    if isinstance(body, dict) and isinstance(body.get("products"), list):
        return {"products": body["products"]}
    raise ManifestError("Request must contain a manifest with a products array.")


def create_app(
    package_root: Path = PACKAGE_ROOT,
    *,
    store: OrchestratorStore | None = None,
    coordinator: RunCoordinator | None = None,
    agent_runtime: Any | None = None,
    start_workers: bool = False,
) -> Flask:
    package_root = package_root.resolve()
    app = Flask(
        __name__,
        template_folder=str(package_root / "web" / "templates"),
        static_folder=str(package_root / "web" / "static"),
    )
    app.config.update(JSON_SORT_KEYS=False, MAX_CONTENT_LENGTH=2 * 1024 * 1024)
    app.secret_key = secrets.token_hex(32)
    orchestration = store or OrchestratorStore(package_root)
    runner = coordinator or RunCoordinator(orchestration)
    app.extensions["orchestrator_store"] = orchestration
    app.extensions["run_coordinator"] = runner
    app.extensions["antigravity_supervisor"] = agent_runtime
    if start_workers:
        runner.start()

    manifest_path = package_root / "input" / "products.json"
    docs_root = package_root / "docs"
    csrf_token = secrets.token_urlsafe(32)

    @app.before_request
    def guard_mutations():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None
        origin = request.headers.get("Origin")
        if origin:
            allowed = {request.host_url.rstrip("/"), f"http://{request.host}"}
            if origin.rstrip("/") not in allowed:
                return jsonify(error="Origin is not allowed."), 403
        if request.headers.get("X-CSRF-Token") != csrf_token:
            return jsonify(error="Invalid CSRF token."), 403
        if request.mimetype != "application/json":
            return jsonify(error="Content-Type must be application/json."), 415
        return None

    @app.errorhandler(KeyError)
    def not_found(error: KeyError):
        return jsonify(error=f"Not found: {error.args[0]}"), 404

    @app.errorhandler(ManifestError)
    @app.errorhandler(ContentValidationError)
    @app.errorhandler(QueueConflict)
    @app.errorhandler(ClaimError)
    @app.errorhandler(ValueError)
    def invalid_request(error: Exception):
        return jsonify(error=str(error)), 400

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/bootstrap")
    def bootstrap():
        manifest = load_json(manifest_path) if manifest_path.is_file() else {"products": []}
        return jsonify(
            csrf_token=csrf_token,
            manifest=manifest,
            options={"headless": True, "dry_run": False, "max_combinations": 100, "amazon_postal_code": "10001"},
            runs=orchestration.list_runs(),
            queue=orchestration.queue_status(),
            product_types=_read_product_types(package_root),
            agent_sessions=orchestration.list_agent_sessions(),
            agent=(agent_runtime.state() if agent_runtime is not None else {
                "status": "disabled", "ready": True, "message": "Agent gate disabled for this app instance."
            }),
        )

    @app.get("/api/agent")
    def agent_status():
        if agent_runtime is None:
            return jsonify(status="disabled", ready=True, message="Agent gate disabled for this app instance.")
        return jsonify(agent_runtime.state())

    @app.get("/api/agent/sessions")
    def list_agent_sessions():
        sessions = orchestration.list_agent_sessions()
        return jsonify(
            sessions=sessions,
            pending_cleanup=sum(item.get("cleanup_status") == "pending_cleanup" for item in sessions),
        )

    @app.post("/api/agent/sessions/<session_id>/open-cleanup")
    def open_agent_cleanup_terminal(session_id: str):
        session = orchestration.agent_session_for_cleanup(session_id)
        executable = getattr(agent_runtime, "executable", "agy") if agent_runtime is not None else "agy"
        pid = _open_antigravity_cleanup_terminal(
            package_root.parent,
            str(session["conversation_id"]),
            executable=executable,
        )
        return jsonify(
            opened=True,
            terminal_pid=pid,
            session_id=session_id,
            conversation_id=session["conversation_id"],
            instructions=[
                "Type /resume in the Antigravity TUI.",
                "Find the displayed conversation ID.",
                "Press Ctrl+Delete, then Enter or Y to confirm.",
                "Return to the dashboard and click Deleted in Antigravity.",
            ],
        )

    @app.post("/api/agent/sessions/<session_id>/acknowledge-cleanup")
    def acknowledge_agent_cleanup(session_id: str):
        return jsonify(orchestration.acknowledge_agent_cleanup(session_id))

    @app.get("/api/docs")
    def list_docs():
        return jsonify(documents=_list_docs(docs_root))

    @app.get("/api/docs/content")
    def read_doc():
        relative_path = str(request.args.get("path", "")).strip()
        document = _resolve_doc_path(docs_root, relative_path)
        content = document.read_text(encoding="utf-8")
        render_format, rendered_html = _render_doc_content(document.suffix, content)
        return jsonify(
            path=document.relative_to(docs_root.resolve()).as_posix(),
            name=document.name,
            extension=document.suffix.lower(),
            content=content,
            format=render_format,
            rendered_html=rendered_html,
        )

    @app.get("/api/prompts")
    def read_prompts():
        return jsonify(**_read_prompts(package_root))

    @app.get("/api/product-types")
    def read_product_types():
        return jsonify(product_types=_read_product_types(package_root), source=PRODUCT_TYPES_FILE)

    @app.put("/api/prompts")
    def save_prompts():
        prompts = _validate_prompts(request.get_json(silent=False))
        for key, filename in PROMPT_FILES.items():
            atomic_write_text(package_root / filename, prompts[key])
        return jsonify(
            saved=True,
            files=PROMPT_FILES,
            restart_required=True,
            message="Prompts saved. They will be used when the server starts its next Antigravity conversation.",
        )

    @app.post("/api/agent/restart")
    def restart_agent():
        if agent_runtime is None:
            return jsonify(error="Antigravity runtime is not configured."), 409
        return jsonify(agent_runtime.restart()), 202

    @app.post("/api/agent/health-check")
    def check_agent_health():
        if agent_runtime is None:
            return jsonify(error="Antigravity runtime is not configured."), 409
        try:
            return jsonify(agent_runtime.health_check())
        except Exception as exc:
            return jsonify(error=str(exc), agent=agent_runtime.state()), 503

    @app.put("/api/manifest")
    def save_manifest():
        payload = _manifest_payload(request.get_json(silent=False))
        parse_manifest_payload(payload, manifest_path)
        atomic_write_json(manifest_path, payload)
        return jsonify(saved=True, manifest=payload)

    @app.post("/api/runs")
    def create_run():
        body = request.get_json(silent=False) or {}
        payload = _manifest_payload(body)
        options = validate_run_options(body.get("options"))
        manifest = parse_manifest_payload(payload, manifest_path)
        atomic_write_json(manifest_path, payload)
        return jsonify(orchestration.create_run(manifest, payload, options)), 201

    @app.get("/api/runs")
    def list_runs():
        return jsonify(runs=orchestration.list_runs())

    @app.get("/api/runs/<run_id>")
    def get_run(run_id: str):
        return jsonify(orchestration.get_run(run_id))

    @app.post("/api/runs/<run_id>/resume-crawl")
    def resume_crawl(run_id: str):
        return jsonify(orchestration.resume_crawl(run_id))

    @app.get("/api/queue")
    def queue_status():
        return jsonify(orchestration.queue_status(request.args.get("run_id") or None))

    @app.get("/api/content-tasks/<task_id>/draft")
    def get_content_draft(task_id: str):
        return jsonify(orchestration.content_task(task_id))

    @app.put("/api/content-tasks/<task_id>/draft")
    def save_content_draft(task_id: str):
        body = request.get_json(silent=False) or {}
        return jsonify(orchestration.save_manual_draft(task_id, body.get("content", body)))

    @app.post("/api/content-tasks/<task_id>/finalize")
    def finalize_content(task_id: str):
        return jsonify(orchestration.finalize_manual_content(task_id))

    @app.post("/api/content-tasks/<task_id>/release")
    def release_content(task_id: str):
        body = request.get_json(silent=False) or {}
        return jsonify(orchestration.force_release_content(task_id, str(body.get("reason", "Released from dashboard."))))

    @app.post("/api/content-tasks/<task_id>/requeue")
    def requeue_content(task_id: str):
        return jsonify(orchestration.return_content_to_queue(task_id))

    @app.post("/api/content-tasks/<task_id>/retry")
    def retry_content(task_id: str):
        return jsonify(orchestration.retry_failed_content(task_id))

    @app.post("/api/apply-tasks/<task_id>/retry")
    def retry_apply(task_id: str):
        return jsonify(orchestration.retry_apply(task_id))

    @app.post("/api/products/<product_id>/acknowledge")
    def acknowledge_product(product_id: str):
        return jsonify(orchestration.acknowledge_product(product_id))

    def event_stream(run_id: str | None):
        try:
            cursor = int(request.args.get("after", request.headers.get("Last-Event-ID", "0")) or 0)
        except ValueError:
            cursor = 0

        @stream_with_context
        def generate():
            nonlocal cursor
            heartbeat = time.monotonic()
            while True:
                for event in orchestration.events_after(cursor, run_id=run_id):
                    cursor = int(event["id"])
                    yield f"id: {cursor}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                if time.monotonic() - heartbeat >= 15:
                    yield ": keep-alive\n\n"
                    heartbeat = time.monotonic()
                time.sleep(0.75)

        return Response(generate(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/runs/<run_id>/events")
    def run_events(run_id: str):
        orchestration.get_run(run_id)
        return event_stream(run_id)

    @app.get("/api/queue/events")
    def queue_events():
        return event_stream(None)

    return app


def serve(host: str = "127.0.0.1", port: int = 5000) -> None:
    from .antigravity import AntigravitySupervisor

    store = OrchestratorStore(PACKAGE_ROOT)
    readiness_gate = threading.Event()
    coordinator = RunCoordinator(store)
    agent = AntigravitySupervisor(PACKAGE_ROOT, store, readiness_gate)
    app = create_app(PACKAGE_ROOT, store=store, coordinator=coordinator, agent_runtime=agent)
    http_server = make_server(host, port, app, threaded=True)
    registration = register_server_process(PACKAGE_ROOT, host, port)
    dashboard_url = _dashboard_url(host, port)
    try:
        coordinator.start()
        agent.start()
        browser_timer = threading.Timer(0.2, _open_dashboard, args=(dashboard_url,))
        browser_timer.daemon = True
        browser_timer.start()
        print(" * Serving Flask app 'scraper.server'", flush=True)
        print(" * Debug mode: off", flush=True)
        print("WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.", flush=True)
        print(f" * Running on {dashboard_url}", flush=True)
        print("Press CTRL+C to quit", flush=True)
        http_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        readiness_gate.clear()
        http_server.server_close()
        coordinator.stop()
        agent.stop()
        unregister_server_process(registration)
