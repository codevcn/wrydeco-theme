import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from scraper.antigravity import (
    AntigravityProtocolError,
    AntigravitySupervisor,
    _sanitize_text,
)
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


def test_one_stream_process_keeps_conversation_across_turns(tmp_path):
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

    store = OrchestratorStore(root)
    gate = threading.Event()
    supervisor = AntigravitySupervisor(root, store, gate, popen_factory=popen_factory)
    supervisor.start()
    wait_for(supervisor.is_ready)
    first = supervisor.state()
    assert first["process_ready"] is True
    result = supervisor._run_turn("second", purpose="test", timeout=5)
    assert result["conversation_id"] == first["conversation_id"] == "conversation-one"
    assert supervisor.state()["pid"] == first["pid"]
    assert supervisor.state()["num_turns"] == 2
    assert len(commands) == 1
    assert "-p" not in commands[0]
    supervisor.stop()


def test_health_check_uses_same_conversation_and_accepts_recent_agent_time(tmp_path):
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
    wait_for(supervisor.is_ready)
    result = supervisor.health_check()
    assert result["active"] is True
    assert result["conversation_id"] == "conversation-health"
    assert result["drift_seconds"] <= 300
    assert supervisor.state()["num_turns"] == 2
    assert supervisor.state()["status"] == "ready"
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

    def popen_factory(command, **kwargs):
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
    sessions = [item for item in store.list_agent_sessions() if item["session_kind"] == "content"]
    assert {item["product_id"] for item in sessions} == {task["task_id"] for task in tasks}
