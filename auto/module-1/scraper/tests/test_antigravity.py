import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from scraper.antigravity import (
    AntigravityFileReadDenied,
    AntigravityProtocolError,
    AntigravitySupervisor,
    _sanitize_text,
    read_antigravity_config,
    save_antigravity_config,
)
from scraper.config import DEFAULT_ANTIGRAVITY_MODEL
from scraper.manifest import parse_manifest_payload
from scraper.store import OrchestratorStore


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "scraper"
    root.mkdir()
    (root / "AGENT_BOOTSTRAP_PROMPT.md").write_text("Bootstrap and reply WRYDECO_AGENT_READY", encoding="utf-8")
    (root / "CONTENT_TASK_PROMPT.md").write_text("Process one task", encoding="utf-8")
    (root / "AGENT_PROMPT.md").write_text("Only factual content.", encoding="utf-8")
    (root / "content.schema.json").write_text("{}", encoding="utf-8")
    return root


def wait_for(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition was not reached")


@pytest.mark.parametrize("queued_before_start", [False, True])
def test_content_demand_starts_one_control_process(tmp_path, monkeypatch, queued_before_start):
    root = make_root(tmp_path)
    fake = tmp_path / "fake_agy.py"
    fake.write_text(
        """
import json, sys
conversation = "conversation-one"
turn = 0
for line in sys.stdin:
    turn += 1
    print(json.dumps({"event":"init","conversation_id":conversation,"init":{"tools":["call_mcp_tool","read_resource"]}}), flush=True) if turn == 1 else None
    if turn == 1:
        print(json.dumps({"event":"step_update","step_update":{"step_type":"tool","state":"DONE","tool_name":"call_mcp_tool","tool_info":{"parameters":{"ServerName":"wrydeco-scraper","ToolName":"queue_status"}}}}), flush=True)
    response = "WRYDECO_AGENT_READY" if turn == 1 else "second turn"
    print(json.dumps({"event":"result","result":{"conversation_id":conversation,"status":"SUCCESS","response":response,"num_turns":turn}}), flush=True)
""",
        encoding="utf-8",
    )
    commands = []

    def popen_factory(command, **kwargs):
        commands.append(command)
        return subprocess.Popen([sys.executable, "-u", str(fake)], **kwargs)

    def enqueue(store):
        payload = {"products": [{
            "amazon_url": "https://www.amazon.com/dp/B000000000", "shopify_product_id": "123",
        }]}
        manifest = parse_manifest_payload(payload, root / "manifest.json")
        run = store.create_run(manifest, payload, {})
        product_id = run["products"]["B000000000"]["id"]
        workspace = store.workspace(store.product(product_id))
        (workspace / "source.json").write_text('{"title": "Table"}', encoding="utf-8")
        for status in ("crawling", "crawled", "price_verified"):
            store.set_product_status(product_id, status)
        store.enqueue_content(product_id)
        return product_id

    store = OrchestratorStore(root)
    if queued_before_start:
        product_id = enqueue(store)
        store = OrchestratorStore(root)
    watcher_waiting = threading.Event()
    wait_for_change = store.wait_for_change

    def observe_wait(timeout):
        watcher_waiting.set()
        wait_for_change(timeout)

    monkeypatch.setattr(store, "wait_for_change", observe_wait)
    gate = threading.Event()
    supervisor = AntigravitySupervisor(root, store, gate, popen_factory=popen_factory)
    dispatched = []

    def finish_task(task):
        store.fail_content_automation(task["task_id"], "Finished test dispatch.", terminal=True)
        dispatched.append(task["task_id"])

    monkeypatch.setattr(supervisor, "_process_isolated_task", finish_task)
    try:
        supervisor.start()
        if not queued_before_start:
            assert watcher_waiting.wait(5)
            assert supervisor.state()["status"] == "waiting"
            assert commands == []
            product_id = enqueue(store)
        wait_for(lambda: dispatched == [product_id])
        first = supervisor.state()
        assert first["process_ready"] is True
        assert first["model"] == DEFAULT_ANTIGRAVITY_MODEL == "Gemini 3.8 Flash (High)"
        result = supervisor._run_turn("second", purpose="test", timeout=5)
        assert result["conversation_id"] == first["conversation_id"] == "conversation-one"
        assert supervisor.state()["pid"] == first["pid"]
        assert supervisor.state()["num_turns"] == 2
        assert len(commands) == 1
        assert "-p" not in commands[0]
        model_idx = commands[0].index("--model")
        assert commands[0][model_idx + 1] == "Gemini 3.8 Flash (High)"
    finally:
        supervisor.stop()


@pytest.mark.parametrize("content", [False, True])
@pytest.mark.parametrize("state", ["ACTIVE", "DONE"])
def test_denied_file_read_logs_only_sanitized_path_and_keeps_guard(tmp_path, content, state):
    root = make_root(tmp_path)
    store = OrchestratorStore(root)
    supervisor = AntigravitySupervisor(root, store, threading.Event())
    path = "C:/gallery/password=path-secret/001.jpg"
    payload = {"event": "step_update", "step_update": {
        "tool_name": "view_file", "state": state, "tool_info": {"parameters": json.dumps({
            "AbsolutePath": path, "claim_token": "parameter-secret", "other": "not-for-logs",
        })},
    }}
    with pytest.raises(AntigravityFileReadDenied) as error:
        if content:
            supervisor._log_content_event(payload, {"session_id": "isolated-session"}, {
                "task_id": "assigned-task", "product": {"run_id": "assigned-run", "asin": "example"},
            })
        else:
            supervisor._log_stream_event(payload, purpose="test")
    entries = store.events_after(0)
    entry = next(e for e in entries if e["event"] == "agent_file_read_denied")
    assert entry["denied_path"].startswith("C:/gallery/password=")
    assert "<redacted>" in entry["denied_path"]
    serialized = json.dumps(entries) + str(error.value)
    assert all(secret not in serialized for secret in ("path-secret", "parameter-secret", "not-for-logs"))
    assert entry["tool"] == "view_file" and entry["state"] == state
    if content:
        assert entry["product_id"] == "assigned-task" and entry["run_id"] == "assigned-run"
        assert entry["session_id"] == "isolated-session"


@pytest.mark.parametrize("path", [r"C:\cache\output.txt", "/cache/output.txt"])
def test_spooled_text_read_still_allowed_with_incremental_metadata(tmp_path, path):
    root = make_root(tmp_path)
    store = OrchestratorStore(root)
    supervisor = AntigravitySupervisor(root, store, threading.Event())
    def send(state, parameters):
        supervisor._log_stream_event({"event": "step_update", "step_update": {
            "tool_name": "view_file", "state": state, "tool_info": {"parameters": parameters},
        }}, purpose="test")
    send("ACTIVE", {})
    send("DONE", {"AbsolutePath": path})
    assert not any(e["event"] == "agent_file_read_denied" for e in store.events_after(0))
    with pytest.raises(AntigravityFileReadDenied, match="<missing>"):
        send("DONE", {})


def test_antigravity_config_file_read_save_and_custom_model_propagation(tmp_path):
    root = make_root(tmp_path)
    initial = read_antigravity_config(root)
    assert initial["model"] == "Gemini 3.8 Flash (High)"
    assert initial["default_model"] == "Gemini 3.8 Flash (High)"
    assert "Gemini 3.8 Flash (High)" in initial["available_models"]

    saved = save_antigravity_config(root, "Claude Sonnet 5.5 (High)")
    assert saved["model"] == "Claude Sonnet 5.5 (High)"
    disk_data = json.loads((root / "antigravity_config.json").read_text(encoding="utf-8"))
    assert disk_data["model"] == "Claude Sonnet 5.5 (High)"

    with pytest.raises(ValueError, match="cannot be empty"):
        save_antigravity_config(root, "   ")

    supervisor = AntigravitySupervisor(root, OrchestratorStore(root), threading.Event())
    cmd = supervisor._command()
    assert "--model" in cmd
    assert cmd[cmd.index("--model") + 1] == "Claude Sonnet 5.5 (High)"
    assert supervisor.state()["model"] == "Claude Sonnet 5.5 (High)"


def test_health_check_starts_idle_runtime_and_uses_bootstrapped_conversation(tmp_path):
    root = make_root(tmp_path)
    fake = tmp_path / "fake_agy_health.py"
    fake.write_text(
        """
import json, sys
from datetime import datetime, timezone
conversation = "conversation-health"
turn = 0
for line in sys.stdin:
    turn += 1
    if turn == 1:
        print(json.dumps({"event":"init","conversation_id":conversation,"init":{"tools":["call_mcp_tool","read_resource"]}}), flush=True)
        print(json.dumps({"event":"step_update","step_update":{"step_type":"tool","state":"DONE","tool_name":"call_mcp_tool","tool_info":{"parameters":{"ServerName":"wrydeco-scraper","ToolName":"queue_status"}}}}), flush=True)
        response = "WRYDECO_AGENT_READY"
    else:
        response = datetime.now(timezone.utc).isoformat()
    print(json.dumps({"event":"result","result":{"conversation_id":conversation,"status":"SUCCESS","response":response,"num_turns":turn}}), flush=True)
""",
        encoding="utf-8",
    )

    def popen_factory(command, **kwargs):
        return subprocess.Popen([sys.executable, "-u", str(fake)], **kwargs)

    store = OrchestratorStore(root)
    gate = threading.Event()
    supervisor = AntigravitySupervisor(root, store, gate, popen_factory=popen_factory)
    supervisor.start()
    try:
        assert supervisor.state()["status"] == "waiting"
        assert supervisor.state()["process_alive"] is False
        result = supervisor.health_check()
        assert result["active"] is True
        assert result["conversation_id"] == "conversation-health"
        assert result["drift_seconds"] <= 300
        assert supervisor.state()["num_turns"] == 2
        assert supervisor.state()["status"] == "ready"
    finally:
        supervisor.stop()


def test_unapproved_tool_call_fails_closed_and_sensitive_log_text_is_redacted(tmp_path):
    root = make_root(tmp_path)
    supervisor = AntigravitySupervisor(root, OrchestratorStore(root), threading.Event())
    with pytest.raises(AntigravityProtocolError, match="unapproved tool"):
        supervisor._log_stream_event({
            "event": "step_update",
            "step_update": {"step_type": "tool", "tool_name": "run_command", "tool_info": {}},
        }, purpose="test")
    sanitized = _sanitize_text('claim_token: "very-secret-value"')
    assert "very-secret-value" not in sanitized
    assert "<redacted>" in sanitized


def test_incremental_mcp_metadata_is_not_rejected_and_resource_discovery_is_safe(tmp_path):
    root = make_root(tmp_path)
    supervisor = AntigravitySupervisor(root, OrchestratorStore(root), threading.Event())

    supervisor._log_stream_event({
        "event": "step_update",
        "step_update": {
            "step_type": "tool", "state": "ACTIVE", "tool_name": "call_mcp_tool",
            "tool_info": {"parameters": {"ServerName": "wrydeco-scraper"}},
        },
    }, purpose="test")

    supervisor._log_stream_event({
        "event": "step_update",
        "step_update": {
            "step_type": "tool", "state": "DONE", "tool_name": "list_resources",
            "tool_info": {"parameters": {"ServerName": "wrydeco-scraper"}},
        },
    }, purpose="test")

    with pytest.raises(AntigravityProtocolError, match="without complete metadata"):
        supervisor._log_stream_event({
            "event": "step_update",
            "step_update": {
                "step_type": "tool", "state": "DONE", "tool_name": "call_mcp_tool",
                "tool_info": {"parameters": {"ServerName": "wrydeco-scraper"}},
            },
        }, purpose="test")


def test_each_product_content_runtime_has_an_isolated_process_and_conversation(tmp_path):
    root = make_root(tmp_path)
    save_antigravity_config(root, "Gemini 3.8 Flash (Medium)")
    fake = tmp_path / "fake_agy_content.py"
    fake.write_text(
        """
import json, os, sys, uuid
conversation = "content-" + uuid.uuid4().hex
for line in sys.stdin:
    print(json.dumps({"event":"init","conversation_id":conversation,"init":{"tools":["call_mcp_tool","read_resource"]}}), flush=True)
    print(json.dumps({"event":"result","result":{"conversation_id":conversation,"status":"SUCCESS","response":"done","num_turns":1}}), flush=True)
""",
        encoding="utf-8",
    )
    commands = []

    def popen_factory(command, **kwargs):
        commands.append(command)
        return subprocess.Popen([sys.executable, "-u", str(fake)], **kwargs)

    store = OrchestratorStore(root)
    payload = {"products": [
        {"amazon_url": "https://www.amazon.com/dp/B000000000", "shopify_product_id": "123", "mode": "auto"},
        {"amazon_url": "https://www.amazon.com/dp/B000000001", "shopify_product_id": "124", "mode": "auto"},
    ]}
    manifest = parse_manifest_payload(payload, root / "manifest.json")
    run = store.create_run(manifest, payload, {"dry_run": True})
    tasks = []
    for product in run["products"].values():
        workspace = store.workspace(store.product(product["id"]))
        (workspace / "source.json").write_text(json.dumps({"title": product["asin"]}), encoding="utf-8")
        for status in ("crawling", "crawled", "price_verified"):
            store.set_product_status(product["id"], status)
        store.enqueue_content(product["id"])
        tasks.append(store.next_queued_content() if not tasks else {
            **store.content_task(product["id"]), "product": store.product(product["id"]),
        })

    supervisor = AntigravitySupervisor(root, store, threading.Event(), popen_factory=popen_factory)
    runtimes = []
    try:
        for task in tasks:
            runtime = supervisor._launch_content_runtime(task)
            supervisor._run_content_turn(runtime, task, "process assigned task", 1)
            runtimes.append(runtime)
    finally:
        for runtime in runtimes:
            supervisor._terminate_child(runtime["process"])

    assert len({runtime["process"].pid for runtime in runtimes}) == 2
    assert len({runtime["conversation_id"] for runtime in runtimes}) == 2
    assert len(commands) == 2
    for cmd in commands:
        assert "--model" in cmd
        assert cmd[cmd.index("--model") + 1] == "Gemini 3.8 Flash (Medium)"
    sessions = [item for item in store.list_agent_sessions() if item["session_kind"] == "content"]
    assert {item["product_id"] for item in sessions} == {task["task_id"] for task in tasks}

