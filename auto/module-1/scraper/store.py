from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .content import (
    content_fingerprints,
    content_similarity,
    source_digest,
    validate_content,
    validate_content_grounding,
    validate_visual_analysis,
    VISUAL_ANALYSIS_SCHEMA,
    validate_visual_keyword_usage,
)
from .errors import ContentValidationError
from .io_utils import atomic_write_json, load_json
from .manifest import Manifest


CONTENT_FIELDS = (
    "title",
    "description_html",
    "seo_product_title",
    "seo_title",
    "seo_description",
    "handle",
)
IMAGE_EVIDENCE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
FINAL_PRODUCT_STATES = {"applied", "dry_run_complete", "failed", "cancelled"}
OPEN_PRODUCT_STATES = {
    "pending", "crawling", "crawled", "price_verified", "content_queued",
    "content_claimed", "content_ready", "apply_queued", "applying", "needs_attention",
}
PRODUCT_TRANSITIONS = {
    "pending": {"crawling", "failed", "needs_attention", "cancelled"},
    "crawling": {"crawling", "crawled", "price_verified", "failed", "needs_attention", "cancelled"},
    "crawled": {"price_verified", "failed", "needs_attention", "cancelled"},
    "price_verified": {"content_queued", "failed", "needs_attention", "cancelled"},
    "content_queued": {"content_claimed", "failed", "needs_attention", "cancelled"},
    "content_claimed": {"content_queued", "content_ready", "failed", "needs_attention", "cancelled"},
    "content_ready": {"content_queued", "apply_queued", "failed", "cancelled"},
    "apply_queued": {"applying", "content_queued", "failed", "needs_attention", "cancelled"},
    "applying": {"applied", "dry_run_complete", "failed", "needs_attention"},
    "needs_attention": {"apply_queued", "content_queued", "cancelled"},
    "failed": {"cancelled"},
    "applied": set(),
    "dry_run_complete": set(),
    "cancelled": set(),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


class QueueConflict(RuntimeError):
    pass


class ClaimError(RuntimeError):
    pass


class OrchestratorStore:
    """SQLite-backed run, queue, lease, and event store.

    SQLite owns orchestration state. Files under runs/ remain the durable product
    artifacts and are reconciled back into the database after a crash.
    """

    def __init__(self, package_root: Path, *, lease_seconds: int = 900):
        self.package_root = package_root.resolve()
        self.runs_root = (self.package_root / "runs").resolve()
        self.runtime_root = (self.package_root / ".runtime").resolve()
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.runtime_root / "orchestrator.sqlite3"
        self.lease_seconds = lease_seconds
        self._condition = threading.Condition()
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _public_value(self, value: Any) -> Any:
        if isinstance(value, str):
            roots = {str(self.package_root), str(self.package_root).replace("\\", "/")}
            output = value
            for root in roots:
                output = output.replace(root, "<scraper>")
            return output
        if isinstance(value, dict):
            return {key: self._public_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._public_value(item) for item in value]
        return value

    @contextmanager
    def transaction(self, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _migrate(self) -> None:
        with self.transaction(immediate=True) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    manifest_digest TEXT NOT NULL,
                    manifest_snapshot_path TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    crawl_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL,
                    asin TEXT NOT NULL,
                    amazon_url TEXT NOT NULL,
                    shopify_product_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    preset_json TEXT,
                    overrides_json TEXT NOT NULL,
                    workspace_rel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    error_type TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(run_id, asin),
                    UNIQUE(run_id, shopify_product_id)
                );
                CREATE INDEX IF NOT EXISTS products_lookup ON products(asin, shopify_product_id, status);
                CREATE TABLE IF NOT EXISTS content_tasks (
                    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
                    state TEXT NOT NULL,
                    queued_at TEXT NOT NULL,
                    claimed_at TEXT,
                    claimed_by TEXT,
                    claim_token_hash TEXT,
                    lease_expires_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    automation_attempts INTEGER NOT NULL DEFAULT 0,
                    last_agent_error TEXT,
                    revision INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    source_digest TEXT,
                    context_read_revision INTEGER,
                    visual_analysis_state TEXT NOT NULL DEFAULT 'pending',
                    uniqueness_attempts INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS content_queue_order ON content_tasks(state, queued_at);
                CREATE TABLE IF NOT EXISTS apply_tasks (
                    product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
                    state TEXT NOT NULL,
                    queued_at TEXT NOT NULL,
                    started_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS apply_queue_order ON apply_tasks(state, queued_at);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    product_id TEXT,
                    source TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS events_run_cursor ON events(run_id, id);
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    id TEXT PRIMARY KEY,
                    generation INTEGER NOT NULL,
                    pid INTEGER,
                    conversation_id TEXT,
                    status TEXT NOT NULL,
                    num_turns INTEGER NOT NULL DEFAULT 0,
                    current_product_id TEXT,
                    started_at TEXT NOT NULL,
                    ready_at TEXT,
                    stopped_at TEXT,
                    last_activity_at TEXT,
                    last_error TEXT,
                    cleanup_status TEXT NOT NULL DEFAULT 'current',
                    cleanup_at TEXT,
                    session_kind TEXT NOT NULL DEFAULT 'control',
                    product_id TEXT,
                    parent_session_id TEXT
                );
                CREATE INDEX IF NOT EXISTS agent_sessions_status ON agent_sessions(status, started_at);
                CREATE TABLE IF NOT EXISTS agent_turns (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    product_id TEXT,
                    attempt INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL,
                    result_status TEXT,
                    error TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS agent_turns_session ON agent_turns(session_id, started_at);
                CREATE TABLE IF NOT EXISTS content_evidence_reads (
                    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    revision INTEGER NOT NULL,
                    evidence_id TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    read_at TEXT NOT NULL,
                    PRIMARY KEY(product_id, revision, evidence_id, worker_id)
                );
                CREATE TABLE IF NOT EXISTS content_fingerprints (
                    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    revision INTEGER NOT NULL,
                    field TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    signature_json TEXT NOT NULL DEFAULT '{}',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(product_id, revision, field)
                );
                CREATE INDEX IF NOT EXISTS content_fingerprints_active ON content_fingerprints(active, field, sha256);
                INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', '4');
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(content_tasks)").fetchall()}
            if "automation_attempts" not in columns:
                connection.execute("ALTER TABLE content_tasks ADD COLUMN automation_attempts INTEGER NOT NULL DEFAULT 0")
            if "last_agent_error" not in columns:
                connection.execute("ALTER TABLE content_tasks ADD COLUMN last_agent_error TEXT")
            if "source_digest" not in columns:
                connection.execute("ALTER TABLE content_tasks ADD COLUMN source_digest TEXT")
            if "context_read_revision" not in columns:
                connection.execute("ALTER TABLE content_tasks ADD COLUMN context_read_revision INTEGER")
            if "visual_analysis_state" not in columns:
                connection.execute(
                    "ALTER TABLE content_tasks ADD COLUMN visual_analysis_state TEXT NOT NULL DEFAULT 'pending'"
                )
            if "uniqueness_attempts" not in columns:
                connection.execute(
                    "ALTER TABLE content_tasks ADD COLUMN uniqueness_attempts INTEGER NOT NULL DEFAULT 0"
                )
            agent_columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_sessions)").fetchall()}
            if "cleanup_status" not in agent_columns:
                connection.execute(
                    "ALTER TABLE agent_sessions ADD COLUMN cleanup_status TEXT NOT NULL DEFAULT 'current'"
                )
                latest = connection.execute(
                    "SELECT id FROM agent_sessions WHERE conversation_id IS NOT NULL "
                    "ORDER BY generation DESC LIMIT 1"
                ).fetchone()
                if latest:
                    connection.execute(
                        "UPDATE agent_sessions SET cleanup_status='pending_cleanup' "
                        "WHERE conversation_id IS NOT NULL AND id<>?",
                        (latest["id"],),
                    )
            if "cleanup_at" not in agent_columns:
                connection.execute("ALTER TABLE agent_sessions ADD COLUMN cleanup_at TEXT")
            if "session_kind" not in agent_columns:
                connection.execute(
                    "ALTER TABLE agent_sessions ADD COLUMN session_kind TEXT NOT NULL DEFAULT 'control'"
                )
            if "product_id" not in agent_columns:
                connection.execute("ALTER TABLE agent_sessions ADD COLUMN product_id TEXT")
            if "parent_session_id" not in agent_columns:
                connection.execute("ALTER TABLE agent_sessions ADD COLUMN parent_session_id TEXT")
            fingerprint_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(content_fingerprints)").fetchall()
            }
            if "signature_json" not in fingerprint_columns:
                connection.execute(
                    "ALTER TABLE content_fingerprints ADD COLUMN signature_json TEXT NOT NULL DEFAULT '{}'"
                )

    def interrupt_agent_sessions(self) -> int:
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            rows = connection.execute(
                "SELECT id, session_kind FROM agent_sessions "
                "WHERE status IN ('starting', 'initializing', 'ready', 'busy', 'stopping')"
            ).fetchall()
            for row in rows:
                connection.execute(
                    """
                    UPDATE agent_sessions SET status='interrupted', stopped_at=?, last_activity_at=?,
                        cleanup_status=CASE WHEN session_kind='content' AND conversation_id IS NOT NULL
                            THEN 'pending_cleanup' ELSE cleanup_status END
                    WHERE id=?
                    """,
                    (now, now, row["id"]),
                )
                if str(row["session_kind"]) == "content":
                    worker_id = f"server-content:{row['id']}"
                    claims = connection.execute(
                        """
                        SELECT ct.product_id, p.run_id, p.asin FROM content_tasks ct
                        JOIN products p ON p.id=ct.product_id
                        WHERE ct.state='claimed' AND ct.claimed_by=?
                        """,
                        (worker_id,),
                    ).fetchall()
                    for claim in claims:
                        reason = "Server restarted; interrupted content claim returned to the queue."
                        connection.execute(
                            """
                            UPDATE content_tasks SET state='queued', claimed_at=NULL, claimed_by=NULL,
                                claim_token_hash=NULL, lease_expires_at=NULL, last_error=?,
                                last_agent_error=?, updated_at=? WHERE product_id=?
                            """,
                            (reason, reason, now, claim["product_id"]),
                        )
                        connection.execute(
                            "UPDATE products SET status='content_queued', updated_at=? WHERE id=?",
                            (now, claim["product_id"]),
                        )
                        self._event_conn(
                            connection, "content_released", run_id=claim["run_id"],
                            product_id=claim["product_id"], source="antigravity", asin=claim["asin"],
                            message=reason,
                        )
            stale_claims = connection.execute(
                """
                SELECT ct.product_id, p.run_id, p.asin FROM content_tasks ct
                JOIN products p ON p.id=ct.product_id
                WHERE ct.state='claimed' AND ct.claimed_by LIKE 'server-content:%'
                  AND NOT EXISTS (
                    SELECT 1 FROM agent_sessions s
                    WHERE ('server-content:' || s.id)=ct.claimed_by
                      AND s.status IN ('starting', 'initializing', 'ready', 'busy', 'stopping')
                  )
                """
            ).fetchall()
            for claim in stale_claims:
                reason = "Server restarted; stale content claim returned to the queue."
                connection.execute(
                    """
                    UPDATE content_tasks SET state='queued', claimed_at=NULL, claimed_by=NULL,
                        claim_token_hash=NULL, lease_expires_at=NULL, last_error=?,
                        last_agent_error=?, updated_at=? WHERE product_id=?
                    """,
                    (reason, reason, now, claim["product_id"]),
                )
                connection.execute(
                    "UPDATE products SET status='content_queued', updated_at=? WHERE id=?",
                    (now, claim["product_id"]),
                )
                self._event_conn(
                    connection, "content_released", run_id=claim["run_id"],
                    product_id=claim["product_id"], source="antigravity", asin=claim["asin"],
                    message=reason,
                )
            return len(rows)

    def create_agent_session(
        self,
        session_id: str,
        *,
        session_kind: str = "control",
        product_id: str | None = None,
        parent_session_id: str | None = None,
    ) -> dict[str, Any]:
        if session_kind not in {"control", "content"}:
            raise ValueError("Agent session_kind must be control or content.")
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            generation = int(connection.execute("SELECT COALESCE(MAX(generation), 0) + 1 FROM agent_sessions").fetchone()[0])
            connection.execute(
                """
                INSERT INTO agent_sessions(
                    id, generation, status, started_at, last_activity_at,
                    session_kind, product_id, parent_session_id
                )
                VALUES (?, ?, 'starting', ?, ?, ?, ?, ?)
                """,
                (session_id, generation, now, now, session_kind, product_id, parent_session_id),
            )
            self._event_conn(
                connection, "agent_status", source="antigravity", status="starting",
                session_id=session_id, generation=generation, session_kind=session_kind,
                product_id=product_id,
                message=("Starting Antigravity content session." if session_kind == "content"
                         else "Starting Antigravity control runtime."),
            )
        return self.agent_session(session_id)

    def update_agent_session(self, session_id: str, status: str, **values: Any) -> dict[str, Any]:
        allowed = {
            "pid", "conversation_id", "num_turns", "current_product_id", "ready_at",
            "stopped_at", "last_activity_at", "last_error",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        updates.setdefault("last_activity_at", utc_now())
        assignments = ["status=?"] + [f"{key}=?" for key in updates]
        params = [status, *updates.values(), session_id]
        with self.transaction(immediate=True) as connection:
            if not connection.execute("SELECT 1 FROM agent_sessions WHERE id=?", (session_id,)).fetchone():
                raise KeyError(session_id)
            connection.execute(
                f"UPDATE agent_sessions SET {', '.join(assignments)} WHERE id=?", params
            )
            conversation_id = updates.get("conversation_id")
            session = connection.execute(
                "SELECT session_kind FROM agent_sessions WHERE id=?", (session_id,)
            ).fetchone()
            session_kind = str(session["session_kind"] if session else "control")
            if conversation_id and session_kind == "control":
                connection.execute(
                    "UPDATE agent_sessions SET cleanup_status='pending_cleanup' "
                    "WHERE id<>? AND session_kind='control' AND conversation_id IS NOT NULL "
                    "AND cleanup_status='current'",
                    (session_id,),
                )
                connection.execute(
                    "UPDATE agent_sessions SET cleanup_status='current', cleanup_at=NULL WHERE id=?",
                    (session_id,),
                )
            elif conversation_id and session_kind == "content":
                connection.execute(
                    "UPDATE agent_sessions SET cleanup_status=? WHERE id=?",
                    ("pending_cleanup" if status in {"stopped", "failed", "interrupted"} else "current", session_id),
                )
            if session_kind == "content" and status in {"stopped", "failed", "interrupted"}:
                connection.execute(
                    "UPDATE agent_sessions SET cleanup_status='pending_cleanup' "
                    "WHERE id=? AND conversation_id IS NOT NULL",
                    (session_id,),
                )
        return self.agent_session(session_id)

    def agent_session(self, session_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            row = connection.execute("SELECT * FROM agent_sessions WHERE id=?", (session_id,)).fetchone()
        finally:
            connection.close()
        if not row:
            raise KeyError(session_id)
        return self._public_value(dict(row))

    def list_agent_sessions(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT s.*, p.asin AS product_asin, COUNT(t.id) AS recorded_turns
                FROM agent_sessions s
                LEFT JOIN agent_turns t ON t.session_id=s.id
                LEFT JOIN products p ON p.id=s.product_id
                WHERE s.conversation_id IS NOT NULL
                GROUP BY s.id
                ORDER BY s.generation DESC
                """
            ).fetchall()
        finally:
            connection.close()
        return [self._public_value(dict(row)) for row in rows]

    def agent_session_for_cleanup(self, session_id: str) -> dict[str, Any]:
        session = self.agent_session(session_id)
        if not session.get("conversation_id"):
            raise QueueConflict("This Agent session has no Antigravity conversation ID.")
        if session.get("cleanup_status") != "pending_cleanup":
            raise QueueConflict("Only a conversation marked pending_cleanup can be cleaned up.")
        return session

    def acknowledge_agent_cleanup(self, session_id: str) -> dict[str, Any]:
        session = self.agent_session_for_cleanup(session_id)
        deleted_events = 0
        with self.transaction(immediate=True) as connection:
            event_ids: list[int] = []
            for row in connection.execute("SELECT id, payload_json FROM events").fetchall():
                payload = _loads(row["payload_json"], {})
                if isinstance(payload, dict) and payload.get("session_id") == session_id:
                    event_ids.append(int(row["id"]))
            if event_ids:
                placeholders = ",".join("?" for _ in event_ids)
                connection.execute(f"DELETE FROM events WHERE id IN ({placeholders})", event_ids)
                deleted_events = len(event_ids)
            cursor = connection.execute(
                "DELETE FROM agent_sessions WHERE id=? AND cleanup_status='pending_cleanup'",
                (session_id,),
            )
            if cursor.rowcount != 1:
                raise QueueConflict("The conversation is no longer pending cleanup.")
        with self._condition:
            self._condition.notify_all()
        return {
            "deleted": True,
            "session_id": session_id,
            "conversation_id": session["conversation_id"],
            "deleted_events": deleted_events,
        }

    def create_agent_turn(
        self, session_id: str, kind: str, *, product_id: str | None = None, attempt: int = 1
    ) -> str:
        turn_id = uuid.uuid4().hex
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO agent_turns(id, session_id, kind, product_id, attempt, status, started_at)
                VALUES (?, ?, ?, ?, ?, 'running', ?)
                """,
                (turn_id, session_id, kind, product_id, attempt, now),
            )
        return turn_id

    def finish_agent_turn(
        self, turn_id: str, status: str, *, result_status: str | None = None, error: str | None = None
    ) -> None:
        with self.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE agent_turns SET status=?, result_status=?, error=?, finished_at=? WHERE id=?
                """,
                (status, result_status, error, utc_now(), turn_id),
            )

    def _event_conn(
        self,
        connection: sqlite3.Connection,
        event_type: str,
        *,
        run_id: str | None = None,
        product_id: str | None = None,
        source: str = "orchestrator",
        **payload: Any,
    ) -> int:
        created_at = utc_now()
        cursor = connection.execute(
            "INSERT INTO events(run_id, product_id, source, type, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, product_id, source, event_type, _json(payload), created_at),
        )
        return int(cursor.lastrowid)

    def event(
        self,
        event_type: str,
        *,
        run_id: str | None = None,
        product_id: str | None = None,
        source: str = "orchestrator",
        **payload: Any,
    ) -> int:
        with self.transaction(immediate=True) as connection:
            event_id = self._event_conn(
                connection, event_type, run_id=run_id, product_id=product_id, source=source, **payload
            )
        with self._condition:
            self._condition.notify_all()
        return event_id

    def wait_for_change(self, timeout: float = 1.0) -> None:
        with self._condition:
            self._condition.wait(timeout)

    def _serialize_event_rows(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        for row in rows:
            payload = self._public_value(_loads(row["payload_json"], {}))
            output.append({
                "id": row["id"], "at": row["created_at"], "event": row["type"],
                "source": row["source"], "run_id": row["run_id"],
                "product_id": row["product_id"], **payload,
            })
        return output

    def events_after(
        self,
        event_id: int,
        *,
        run_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return a bounded event page after a cursor.

        Bounding the page prevents a new SSE client from flooding the browser with
        the complete lifetime history in one response.
        """
        safe_limit = max(1, min(int(limit), 500))
        connection = self._connect()
        try:
            if run_id:
                rows = connection.execute(
                    "SELECT * FROM events WHERE id > ? AND run_id = ? ORDER BY id LIMIT ?",
                    (event_id, run_id, safe_limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM events WHERE id > ? ORDER BY id LIMIT ?", (event_id, safe_limit)
                ).fetchall()
        finally:
            connection.close()
        return self._serialize_event_rows(rows)

    def recent_events(self, limit: int = 250, *, run_id: str | None = None) -> list[dict[str, Any]]:
        """Return only the newest events, ordered oldest-to-newest for display."""
        safe_limit = max(1, min(int(limit), 500))
        connection = self._connect()
        try:
            if run_id:
                rows = connection.execute(
                    "SELECT * FROM events WHERE run_id = ? ORDER BY id DESC LIMIT ?",
                    (run_id, safe_limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM events ORDER BY id DESC LIMIT ?", (safe_limit,)
                ).fetchall()
        finally:
            connection.close()
        return self._serialize_event_rows(list(reversed(rows)))

    def create_run(self, manifest: Manifest, manifest_payload: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
        run_id = uuid.uuid4().hex
        run_root = self.runs_root / run_id
        snapshot_path = run_root / "manifest.json"
        now = utc_now()
        try:
            with self.transaction(immediate=True) as connection:
                for item in manifest.products:
                    conflict = connection.execute(
                        """
                        SELECT p.asin, p.shopify_product_id, p.run_id, p.status
                        FROM products p
                        WHERE (p.asin = ? OR p.shopify_product_id = ?)
                          AND p.status NOT IN ('applied', 'dry_run_complete', 'failed', 'cancelled')
                        LIMIT 1
                        """,
                        (item.asin, item.shopify_product_id),
                    ).fetchone()
                    if conflict:
                        raise QueueConflict(
                            f"{item.asin}/{item.shopify_product_id} is already open in run {conflict['run_id']} "
                            f"with status {conflict['status']}."
                        )
                run_root.mkdir(parents=True, exist_ok=False)
                atomic_write_json(snapshot_path, manifest_payload)
                connection.execute(
                    "INSERT INTO runs VALUES (?, ?, ?, ?, 'queued', ?, ?)",
                    (run_id, manifest.digest, str(snapshot_path), _json(options), now, now),
                )
                for ordinal, item in enumerate(manifest.products):
                    product_id = uuid.uuid4().hex
                    workspace_rel = f"{run_id}/{item.asin}"
                    (self.runs_root / workspace_rel / "evidence").mkdir(parents=True, exist_ok=True)
                    connection.execute(
                        """
                        INSERT INTO products(
                            id, run_id, ordinal, asin, amazon_url, shopify_product_id, mode,
                            preset_json, overrides_json, workspace_rel, status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                        """,
                        (
                            product_id, run_id, ordinal, item.asin, item.amazon_url, item.shopify_product_id,
                            item.mode, _json(item.preset) if item.preset else None, _json(item.overrides),
                            workspace_rel, now, now,
                        ),
                    )
                self._event_conn(connection, "run_created", run_id=run_id, products=len(manifest.products))
        except Exception:
            if run_root.exists():
                shutil.rmtree(run_root)
            raise
        with self._condition:
            self._condition.notify_all()
        return self.get_run(run_id)

    def _product_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "run_id": row["run_id"], "ordinal": row["ordinal"],
            "asin": row["asin"], "amazon_url": row["amazon_url"],
            "shopify_product_id": row["shopify_product_id"], "mode": row["mode"],
            "preset": _loads(row["preset_json"], None), "overrides": _loads(row["overrides_json"], {}),
            "workspace_rel": row["workspace_rel"], "status": row["status"],
            "error": row["error"], "error_type": row["error_type"],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
        }

    def product(self, product_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            row = connection.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        finally:
            connection.close()
        if not row:
            raise KeyError(product_id)
        return self._product_dict(row)

    def products_for_run(self, run_id: str) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM products WHERE run_id = ? ORDER BY ordinal", (run_id,)
            ).fetchall()
        finally:
            connection.close()
        return [self._product_dict(row) for row in rows]

    def workspace(self, product: dict[str, Any]) -> Path:
        target = (self.runs_root / product["workspace_rel"]).resolve()
        if target != self.runs_root and self.runs_root not in target.parents:
            raise ValueError("Product workspace escaped the runs directory.")
        return target

    def _derive_run_status(self, crawl_status: str, products: list[dict[str, Any]]) -> str:
        statuses = {item["status"] for item in products}
        if crawl_status in {"queued", "running"}:
            return "crawling"
        if crawl_status == "interrupted":
            return "interrupted"
        if statuses and statuses <= {"applied", "dry_run_complete", "cancelled"}:
            return "completed"
        if statuses & {"applying", "apply_queued", "content_ready"}:
            return "applying"
        if statuses & {"content_queued", "content_claimed", "price_verified", "crawled", "pending"}:
            return "waiting_for_content"
        if statuses & {"failed", "needs_attention"}:
            return "completed_with_errors"
        return "waiting_for_content"

    def get_run(self, run_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        finally:
            connection.close()
        if not row:
            raise KeyError(run_id)
        products = self.products_for_run(run_id)
        status = self._derive_run_status(row["crawl_status"], products)
        return {
            "id": row["id"], "run_id": row["id"], "manifest_digest": row["manifest_digest"],
            "crawl_status": row["crawl_status"], "status": status,
            "options": _loads(row["options_json"], {}),
            "created_at": row["created_at"], "updated_at": row["updated_at"],
            "products": {item["asin"]: self.product_status(item) for item in products},
        }

    def run_record(self, run_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        finally:
            connection.close()
        if not row:
            raise KeyError(run_id)
        return {
            "id": row["id"], "manifest_digest": row["manifest_digest"],
            "manifest_snapshot_path": row["manifest_snapshot_path"],
            "options": _loads(row["options_json"], {}), "crawl_status": row["crawl_status"],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
        }

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            ids = [row[0] for row in connection.execute(
                "SELECT id FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()]
        finally:
            connection.close()
        return [self.get_run(run_id) for run_id in ids]

    def product_status(self, product: dict[str, Any]) -> dict[str, Any]:
        connection = self._connect()
        try:
            content = connection.execute(
                "SELECT state, queued_at, claimed_by, lease_expires_at, attempts, automation_attempts, "
                "last_agent_error, revision, last_error, source_digest, context_read_revision, "
                "visual_analysis_state, uniqueness_attempts "
                "FROM content_tasks WHERE product_id = ?", (product["id"],)
            ).fetchone()
            apply = connection.execute(
                "SELECT state, attempts, last_error FROM apply_tasks WHERE product_id = ?", (product["id"],)
            ).fetchone()
            queue_position = None
            if content and content["state"] == "queued":
                queue_position = int(connection.execute(
                    """
                    SELECT COUNT(*) + 1 FROM content_tasks candidate
                    JOIN products cp ON cp.id=candidate.product_id
                    WHERE candidate.state='queued' AND (
                        candidate.queued_at < ? OR
                        (candidate.queued_at = ? AND cp.ordinal < ?) OR
                        (candidate.queued_at = ? AND cp.ordinal = ? AND candidate.product_id < ?)
                    )
                    """,
                    (
                        content["queued_at"], content["queued_at"], product["ordinal"],
                        content["queued_at"], product["ordinal"], product["id"],
                    ),
                ).fetchone()[0])
        finally:
            connection.close()
        result = dict(product)
        result.pop("workspace_rel", None)
        result["content_task"] = dict(content) if content else None
        if result["content_task"] is not None:
            result["content_task"]["queue_position"] = queue_position
        result["apply_task"] = dict(apply) if apply else None
        progress_path = self.workspace(product) / "apply_progress.json"
        progress = load_json(progress_path) if progress_path.exists() else {}
        result["shopify_checkpoint"] = {
            key: bool(progress.get(key))
            for key in ("product_set", "new_media_ids", "media_verified", "old_media_deleted", "metafields_set", "published")
            if progress.get(key)
        }
        return self._public_value(result)

    def set_run_crawl_status(self, run_id: str, status: str, *, message: str | None = None) -> None:
        if status not in {"queued", "running", "complete", "interrupted"}:
            raise ValueError(f"Invalid crawl status: {status}")
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            if not connection.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone():
                raise KeyError(run_id)
            connection.execute("UPDATE runs SET crawl_status = ?, updated_at = ? WHERE id = ?", (status, now, run_id))
            self._event_conn(connection, "crawl_status", run_id=run_id, status=status, message=message or status)
        with self._condition:
            self._condition.notify_all()

    def claim_next_crawl_run(self) -> str | None:
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            if connection.execute("SELECT 1 FROM runs WHERE crawl_status = 'running' LIMIT 1").fetchone():
                return None
            row = connection.execute(
                "SELECT id FROM runs WHERE crawl_status = 'queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                return None
            run_id = str(row["id"])
            connection.execute("UPDATE runs SET crawl_status = 'running', updated_at = ? WHERE id = ?", (now, run_id))
            self._event_conn(connection, "crawl_status", run_id=run_id, status="running", message="Crawler started.")
        with self._condition:
            self._condition.notify_all()
        return run_id

    def resume_crawl(self, run_id: str) -> dict[str, Any]:
        with self.transaction(immediate=True) as connection:
            row = connection.execute("SELECT crawl_status FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                raise KeyError(run_id)
            if row["crawl_status"] != "interrupted":
                raise QueueConflict("Only an interrupted crawl can be resumed.")
            connection.execute("UPDATE runs SET crawl_status = 'queued', updated_at = ? WHERE id = ?", (utc_now(), run_id))
            self._event_conn(connection, "crawl_resumed", run_id=run_id, message="Crawler queued from checkpoints.")
        with self._condition:
            self._condition.notify_all()
        return self.get_run(run_id)

    def set_product_status(
        self, product_id: str, status: str, *, error: str | None = None, error_type: str | None = None,
        source: str = "orchestrator", **event_payload: Any,
    ) -> None:
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            row = connection.execute("SELECT run_id, asin, status FROM products WHERE id = ?", (product_id,)).fetchone()
            if not row:
                raise KeyError(product_id)
            allowed = PRODUCT_TRANSITIONS.get(str(row["status"]), set())
            if status != row["status"] and status not in allowed:
                raise QueueConflict(f"Invalid product transition: {row['status']} -> {status}.")
            connection.execute(
                "UPDATE products SET status = ?, error = ?, error_type = ?, updated_at = ? WHERE id = ?",
                (status, error, error_type, now, product_id),
            )
            self._event_conn(
                connection, "product_status", run_id=row["run_id"], product_id=product_id,
                source=source, asin=row["asin"], status=status, error=error,
                error_type=error_type, **event_payload,
            )
            connection.execute("UPDATE runs SET updated_at = ? WHERE id = ?", (now, row["run_id"]))
        with self._condition:
            self._condition.notify_all()

    def enqueue_content(self, product_id: str) -> None:
        product = self.product(product_id)
        if product["status"] not in {"price_verified", "content_queued", "content_claimed"}:
            raise QueueConflict(f"Cannot enqueue content from product status {product['status']}.")
        workspace = self.workspace(product)
        workspace.mkdir(parents=True, exist_ok=True)
        draft_path = workspace / "content.temp.json"
        content_path = workspace / "content.json"
        if not draft_path.exists() and not content_path.exists():
            atomic_write_json(draft_path, {field: "" for field in CONTENT_FIELDS})
        source_path = workspace / "source.json"
        if not source_path.is_file():
            raise QueueConflict("source.json is required before content can be queued.")
        digest = source_digest(source_path)
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO content_tasks(
                    product_id, state, queued_at, source_digest, visual_analysis_state, updated_at
                )
                VALUES (?, 'queued', ?, ?, 'pending', ?)
                ON CONFLICT(product_id) DO UPDATE SET
                    state = CASE WHEN content_tasks.state IN ('ready', 'claimed') THEN content_tasks.state ELSE 'queued' END,
                    automation_attempts = CASE WHEN content_tasks.state='ready' THEN content_tasks.automation_attempts ELSE 0 END,
                    last_agent_error = CASE WHEN content_tasks.state='ready' THEN content_tasks.last_agent_error ELSE NULL END,
                    source_digest = excluded.source_digest,
                    context_read_revision = CASE WHEN content_tasks.state='ready' THEN content_tasks.context_read_revision ELSE NULL END,
                    visual_analysis_state = CASE WHEN content_tasks.state='ready' THEN content_tasks.visual_analysis_state ELSE 'pending' END,
                    updated_at = excluded.updated_at
                """,
                (product_id, now, digest, now),
            )
            connection.execute(
                "UPDATE products SET status = 'content_queued', error = NULL, error_type = NULL, updated_at = ? WHERE id = ?",
                (now, product_id),
            )
            self._event_conn(
                connection, "content_queued", run_id=product["run_id"], product_id=product_id,
                asin=product["asin"], status="content_queued",
            )
        with self._condition:
            self._condition.notify_all()

    def _expire_leases_conn(self, connection: sqlite3.Connection) -> int:
        now = utc_now()
        rows = connection.execute(
            """
            SELECT ct.product_id, p.run_id, p.asin FROM content_tasks ct
            JOIN products p ON p.id = ct.product_id
            WHERE ct.state = 'claimed' AND ct.lease_expires_at < ?
            """,
            (now,),
        ).fetchall()
        for row in rows:
            connection.execute(
                """
                UPDATE content_tasks SET state='queued', claimed_at=NULL, claimed_by=NULL,
                    claim_token_hash=NULL, lease_expires_at=NULL, updated_at=? WHERE product_id=?
                """,
                (now, row["product_id"]),
            )
            connection.execute(
                "UPDATE products SET status='content_queued', updated_at=? WHERE id=?",
                (now, row["product_id"]),
            )
            self._event_conn(
                connection, "content_lease_expired", run_id=row["run_id"], product_id=row["product_id"],
                source="mcp", asin=row["asin"], message="Expired content claim returned to the queue.",
            )
        return len(rows)

    def claim_next_content(self, worker_id: str, *, run_id: str | None = None) -> dict[str, Any] | None:
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        lease = (now_dt + timedelta(seconds=self.lease_seconds)).isoformat()
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.transaction(immediate=True) as connection:
            self._expire_leases_conn(connection)
            sql = (
                "SELECT ct.product_id FROM content_tasks ct JOIN products p ON p.id=ct.product_id "
                "WHERE ct.state='queued'"
            )
            params: list[Any] = []
            if run_id:
                sql += " AND p.run_id=?"
                params.append(run_id)
            sql += " ORDER BY ct.queued_at, p.ordinal, ct.product_id LIMIT 1"
            row = connection.execute(sql, params).fetchone()
            if not row:
                return None
            product_id = str(row["product_id"])
            connection.execute(
                """
                UPDATE content_tasks SET state='claimed', claimed_at=?, claimed_by=?, claim_token_hash=?,
                    lease_expires_at=?, attempts=attempts+1, updated_at=? WHERE product_id=?
                """,
                (now, worker_id, token_hash, lease, now, product_id),
            )
            product_row = connection.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            connection.execute(
                "UPDATE products SET status='content_claimed', updated_at=? WHERE id=?", (now, product_id)
            )
            self._event_conn(
                connection, "content_claimed", run_id=product_row["run_id"], product_id=product_id,
                source="mcp", asin=product_row["asin"], worker_id=worker_id, lease_expires_at=lease,
            )
        with self._condition:
            self._condition.notify_all()
        product = self.product(product_id)
        return {"task_id": product_id, "claim_token": token, "lease_expires_at": lease, "product": self._public_task_product(product)}

    def claim_expected_content(self, worker_id: str, product_id: str) -> dict[str, Any]:
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        lease = (now_dt + timedelta(seconds=self.lease_seconds)).isoformat()
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.transaction(immediate=True) as connection:
            self._expire_leases_conn(connection)
            row = connection.execute(
                """
                SELECT ct.product_id, p.run_id, p.asin FROM content_tasks ct
                JOIN products p ON p.id=ct.product_id
                WHERE ct.product_id=? AND ct.state='queued'
                """,
                (product_id,),
            ).fetchone()
            if not row:
                raise QueueConflict("The expected content task is not queued or no longer exists.")
            connection.execute(
                """
                UPDATE content_tasks SET state='claimed', claimed_at=?, claimed_by=?, claim_token_hash=?,
                    lease_expires_at=?, attempts=attempts+1, context_read_revision=NULL,
                    visual_analysis_state='pending', updated_at=? WHERE product_id=?
                """,
                (now, worker_id, token_hash, lease, now, product_id),
            )
            product_row = connection.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            connection.execute(
                "UPDATE products SET status='content_claimed', updated_at=? WHERE id=?", (now, product_id)
            )
            self._event_conn(
                connection, "content_claimed", run_id=product_row["run_id"], product_id=product_id,
                source="mcp", asin=product_row["asin"], worker_id=worker_id,
                lease_expires_at=lease, expected=True,
            )
        with self._condition:
            self._condition.notify_all()
        product = self.product(product_id)
        return {
            "task_id": product_id,
            "claim_token": token,
            "lease_expires_at": lease,
            "product": self._public_task_product(product),
        }

    def next_queued_content(self) -> dict[str, Any] | None:
        with self.transaction(immediate=True) as connection:
            self._expire_leases_conn(connection)
            row = connection.execute(
                """
                SELECT ct.product_id, ct.revision, ct.automation_attempts, ct.last_agent_error
                FROM content_tasks ct JOIN products p ON p.id=ct.product_id
                WHERE ct.state='queued'
                ORDER BY ct.queued_at, p.ordinal, ct.product_id LIMIT 1
                """
            ).fetchone()
        if not row:
            return None
        product = self.product(str(row["product_id"]))
        return {
            "task_id": product["id"], "revision": int(row["revision"]),
            "automation_attempts": int(row["automation_attempts"]),
            "last_agent_error": row["last_agent_error"], "product": self._public_task_product(product),
        }

    def begin_content_automation_attempt(self, product_id: str) -> int:
        product = self.product(product_id)
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            row = connection.execute(
                "SELECT state, automation_attempts FROM content_tasks WHERE product_id=?", (product_id,)
            ).fetchone()
            if not row or row["state"] != "queued":
                raise QueueConflict("Only a queued content task can start an automated Agent attempt.")
            attempt = int(row["automation_attempts"]) + 1
            connection.execute(
                "UPDATE content_tasks SET automation_attempts=?, last_agent_error=NULL, updated_at=? WHERE product_id=?",
                (attempt, now, product_id),
            )
            self._event_conn(
                connection, "agent_content_attempt", run_id=product["run_id"], product_id=product_id,
                source="antigravity", asin=product["asin"], attempt=attempt,
                message=f"Antigravity content attempt {attempt}.",
            )
        return attempt

    def fail_content_automation(
        self, product_id: str, error: str, *, terminal: bool, worker_id: str | None = None
    ) -> dict[str, Any]:
        product = self.product(product_id)
        now = utc_now()
        clean = str(error).strip()[:2000] or "Antigravity did not finalize content."
        with self.transaction(immediate=True) as connection:
            task = connection.execute(
                "SELECT state, claimed_by FROM content_tasks WHERE product_id=?", (product_id,)
            ).fetchone()
            if not task:
                raise KeyError(product_id)
            if task["state"] == "ready":
                return self.product_status(product)
            if task["state"] == "claimed" and worker_id and task["claimed_by"] != worker_id:
                raise QueueConflict("Content task is claimed by another Agent session.")
            state = "error" if terminal else "queued"
            connection.execute(
                """
                UPDATE content_tasks SET state=?, claimed_at=NULL, claimed_by=NULL,
                    claim_token_hash=NULL, lease_expires_at=NULL, last_error=?, last_agent_error=?, updated_at=?
                WHERE product_id=?
                """,
                (state, clean, clean, now, product_id),
            )
            product_status = "needs_attention" if terminal else "content_queued"
            connection.execute(
                "UPDATE products SET status=?, error=?, error_type=?, updated_at=? WHERE id=?",
                (product_status, clean if terminal else None, "AntigravityContentError" if terminal else None, now, product_id),
            )
            self._event_conn(
                connection, "agent_content_failed" if terminal else "agent_content_retry",
                run_id=product["run_id"], product_id=product_id, source="antigravity", asin=product["asin"],
                status=product_status, message=clean,
            )
        with self._condition:
            self._condition.notify_all()
        return self.product_status(self.product(product_id))

    def release_claims_for_worker(self, worker_id: str, reason: str) -> int:
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            rows = connection.execute(
                """
                SELECT ct.product_id, p.run_id, p.asin FROM content_tasks ct
                JOIN products p ON p.id=ct.product_id
                WHERE ct.state='claimed' AND ct.claimed_by=?
                """,
                (worker_id,),
            ).fetchall()
            for row in rows:
                connection.execute(
                    """
                    UPDATE content_tasks SET state='queued', claimed_at=NULL, claimed_by=NULL,
                        claim_token_hash=NULL, lease_expires_at=NULL, last_error=?, last_agent_error=?, updated_at=?
                    WHERE product_id=?
                    """,
                    (reason, reason, now, row["product_id"]),
                )
                connection.execute(
                    "UPDATE products SET status='content_queued', updated_at=? WHERE id=?",
                    (now, row["product_id"]),
                )
                self._event_conn(
                    connection, "content_released", run_id=row["run_id"], product_id=row["product_id"],
                    source="antigravity", asin=row["asin"], message=reason,
                )
        if rows:
            with self._condition:
                self._condition.notify_all()
        return len(rows)

    @staticmethod
    def _public_task_product(product: dict[str, Any]) -> dict[str, Any]:
        return {
            key: product[key]
            for key in ("id", "run_id", "ordinal", "asin", "amazon_url", "shopify_product_id", "mode", "preset", "overrides", "status")
        }

    def _require_claim_conn(self, connection: sqlite3.Connection, product_id: str, token: str) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT ct.*, p.run_id, p.asin FROM content_tasks ct
            JOIN products p ON p.id=ct.product_id WHERE ct.product_id=?
            """,
            (product_id,),
        ).fetchone()
        if not row or row["state"] != "claimed":
            raise ClaimError("Content task is not currently claimed.")
        expected = row["claim_token_hash"] or ""
        actual = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not secrets.compare_digest(expected, actual):
            raise ClaimError("Invalid claim token.")
        if not row["lease_expires_at"] or row["lease_expires_at"] < utc_now():
            raise ClaimError("Content task lease has expired.")
        return row

    def require_claim(self, product_id: str, token: str) -> dict[str, Any]:
        with self.transaction() as connection:
            self._require_claim_conn(connection, product_id, token)
        return self.product(product_id)

    def renew_content_lease(self, product_id: str, token: str) -> dict[str, Any]:
        now_dt = datetime.now(timezone.utc)
        lease = (now_dt + timedelta(seconds=self.lease_seconds)).isoformat()
        with self.transaction(immediate=True) as connection:
            row = self._require_claim_conn(connection, product_id, token)
            connection.execute(
                "UPDATE content_tasks SET lease_expires_at=?, updated_at=? WHERE product_id=?",
                (lease, now_dt.isoformat(), product_id),
            )
            self._event_conn(
                connection, "content_lease_renewed", run_id=row["run_id"], product_id=product_id,
                source="mcp", asin=row["asin"], lease_expires_at=lease,
            )
        return {"task_id": product_id, "lease_expires_at": lease}

    def content_context(self, product_id: str, token: str) -> dict[str, Any]:
        product = self.require_claim(product_id, token)
        workspace = self.workspace(product)
        source_path = workspace / "source.json"
        pricing_path = workspace / "pricing.json"
        draft_path = workspace / "content.temp.json"
        with self.transaction(immediate=True) as connection:
            row = self._require_claim_conn(connection, product_id, token)
            revision = int(row["revision"])
            connection.execute(
                "UPDATE content_tasks SET context_read_revision=?, updated_at=? WHERE product_id=?",
                (revision, utc_now(), product_id),
            )
        self.event(
            "content_context_read", run_id=product["run_id"], product_id=product_id,
            source="mcp", asin=product["asin"], revision=revision,
            message="Agent read the current product context.",
        )
        source = load_json(source_path) if source_path.exists() else {}
        # A+ text remains valid factual evidence, but its images are reserved for
        # Shopify rich-media handling and must never enter the content Agent's
        # visual context. Removing HTML also prevents embedded A+ image URLs from
        # being surfaced indirectly through get_content_context.
        agent_source = dict(source) if isinstance(source, dict) else {}
        agent_source.pop("aplus_images", None)
        agent_source.pop("aplus_html", None)
        return {
            "task": self._public_task_product(product),
            "revision": revision,
            "source_digest": source_digest(source_path),
            "source": agent_source,
            "pricing": load_json(pricing_path) if pricing_path.exists() else {},
            "draft": load_json(draft_path) if draft_path.exists() else {field: "" for field in CONTENT_FIELDS},
            "rules": (self.package_root / "AGENT_PROMPT.md").read_text(encoding="utf-8"),
            "schema": load_json(self.package_root / "content.schema.json"),
            "visual_analysis_schema": VISUAL_ANALYSIS_SCHEMA,
        }

    def list_evidence(self, product_id: str, token: str) -> list[dict[str, Any]]:
        product = self.require_claim(product_id, token)
        root = self.workspace(product) / "evidence"
        if not root.exists():
            return []
        output = []
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(root).as_posix()
            suffix = path.suffix.casefold()
            if suffix in IMAGE_EVIDENCE_SUFFIXES and not relative.startswith("gallery/"):
                continue
            mime = {
                ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp", ".gif": "image/gif", ".html": "text/html",
                ".txt": "text/plain", ".json": "application/json",
            }.get(suffix, "application/octet-stream")
            output.append({"evidence_id": relative, "mime_type": mime, "size": path.stat().st_size})
        return output

    def evidence_path(self, product_id: str, token: str, evidence_id: str) -> tuple[Path, str]:
        product = self.require_claim(product_id, token)
        root = (self.workspace(product) / "evidence").resolve()
        target = (root / evidence_id).resolve()
        if target == root or root not in target.parents or not target.is_file():
            raise KeyError(evidence_id)
        entry = next((item for item in self.list_evidence(product_id, token) if item["evidence_id"] == evidence_id), None)
        if not entry:
            raise KeyError(evidence_id)
        if target.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("Evidence file exceeds the 10 MiB MCP limit.")
        with self.transaction(immediate=True) as connection:
            row = self._require_claim_conn(connection, product_id, token)
            connection.execute(
                """
                INSERT OR REPLACE INTO content_evidence_reads(
                    product_id, revision, evidence_id, mime_type, worker_id, read_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id, int(row["revision"]), evidence_id, str(entry["mime_type"]),
                    str(row["claimed_by"] or "unknown"), utc_now(),
                ),
            )
        is_image = str(entry["mime_type"]).startswith("image/")
        self.event(
            "visual_evidence_read" if is_image else "content_evidence_read",
            run_id=product["run_id"], product_id=product_id,
            source="mcp", asin=product["asin"], evidence_id=evidence_id,
            mime_type=str(entry["mime_type"]),
            message=(f"Agent read gallery image evidence {evidence_id}." if is_image
                     else f"Agent read content evidence {evidence_id}."),
        )
        return target, str(entry["mime_type"])

    def _visual_requirements_conn(
        self, connection: sqlite3.Connection, product_id: str, token: str
    ) -> tuple[sqlite3.Row, set[str], set[str]]:
        row = self._require_claim_conn(connection, product_id, token)
        revision = int(row["revision"])
        reads = connection.execute(
            """
            SELECT evidence_id, mime_type FROM content_evidence_reads
            WHERE product_id=? AND revision=? AND worker_id=?
            """,
            (product_id, revision, str(row["claimed_by"] or "unknown")),
        ).fetchall()
        read_images = {str(item["evidence_id"]) for item in reads if str(item["mime_type"]).startswith("image/")}
        required = {"gallery/contact-sheet.jpg", "gallery/001.jpg"}
        product = self.product(product_id)
        gallery = self.workspace(product) / "evidence" / "gallery"
        if (gallery / "002.jpg").is_file():
            required.add("gallery/002.jpg")
        return row, read_images, required

    def write_visual_analysis(self, product_id: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        product = self.require_claim(product_id, token)
        workspace = self.workspace(product)
        with self.transaction(immediate=True) as connection:
            row, read_images, required = self._visual_requirements_conn(connection, product_id, token)
            if row["context_read_revision"] is None or int(row["context_read_revision"]) != int(row["revision"]):
                raise ClaimError("Read the current product context before writing visual analysis.")
            missing = sorted(required - read_images)
            if missing:
                raise ClaimError("Required image evidence has not been read: " + ", ".join(missing))
            expected_digest = str(row["source_digest"] or source_digest(workspace / "source.json"))
        normalized = validate_visual_analysis(
            payload,
            expected_task_id=product_id,
            expected_source_digest=expected_digest,
            allowed_evidence_ids=read_images,
        )
        atomic_write_json(workspace / "visual_analysis.json", normalized)
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            self._require_claim_conn(connection, product_id, token)
            connection.execute(
                "UPDATE content_tasks SET visual_analysis_state='ready', updated_at=? WHERE product_id=?",
                (now, product_id),
            )
            self._event_conn(
                connection, "visual_keywords_ready", run_id=product["run_id"], product_id=product_id,
                source="mcp", asin=product["asin"],
                keywords=[*normalized["design_keywords"], *normalized["shape_keywords"]],
                message="Visual design and shape keywords are ready.",
            )
        return {"task_id": product_id, "saved": True, "visual_analysis": normalized}

    def write_content_draft(self, product_id: str, token: str, content: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(content, dict):
            raise ValueError("Content draft must be a JSON object.")
        product = self.require_claim(product_id, token)
        workspace = self.workspace(product)
        with self.transaction(immediate=True) as connection:
            row, read_images, required = self._visual_requirements_conn(connection, product_id, token)
            if row["context_read_revision"] is None or int(row["context_read_revision"]) != int(row["revision"]):
                raise ClaimError("Read the current product context before writing a content draft.")
            if str(row["visual_analysis_state"]) != "ready":
                raise ClaimError("Complete and save visual analysis before writing a content draft.")
            missing = sorted(required - read_images)
            if missing:
                raise ClaimError("Required image evidence has not been read in this Agent session: " + ", ".join(missing))
            current_digest = source_digest(workspace / "source.json")
            if str(row["source_digest"] or "") != current_digest:
                raise ClaimError("Product source changed after the content task was queued; requeue the task.")
        visual_path = workspace / "visual_analysis.json"
        if not visual_path.is_file():
            raise ClaimError("visual_analysis.json is missing.")
        validate_visual_analysis(
            visual_path,
            expected_task_id=product_id,
            expected_source_digest=current_digest,
        )
        atomic_write_json(workspace / "content.temp.json", content)
        self.event(
            "content_draft_saved", run_id=product["run_id"], product_id=product_id,
            source="mcp", asin=product["asin"], message="content.temp.json saved atomically.",
        )
        return {"task_id": product_id, "saved": True}

    def validate_content_draft(self, product_id: str, token: str) -> dict[str, str]:
        product = self.require_claim(product_id, token)
        path = self.workspace(product) / "content.temp.json"
        if not path.is_file():
            raise ContentValidationError("content.temp.json does not exist.")
        return self._validate_complete_content(product, path, record_events=True)

    def _content_collisions(self, product_id: str, content: dict[str, str]) -> list[dict[str, Any]]:
        thresholds = {
            "title": 0.88,
            "seo_product_title": 0.88,
            "seo_title": 0.88,
            "seo_description": 0.85,
            "description_html": 0.82,
            "handle": 1.0,
        }
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT cf.product_id, cf.field, cf.normalized_text, cf.sha256,
                       p.asin, p.shopify_product_id
                FROM content_fingerprints cf
                JOIN products p ON p.id=cf.product_id
                WHERE cf.active=1 AND cf.product_id<>?
                """,
                (product_id,),
            ).fetchall()
        finally:
            connection.close()
        current = content_fingerprints(content)
        collisions: list[dict[str, Any]] = []
        for row in rows:
            field = str(row["field"])
            if field not in current or field not in thresholds:
                continue
            exact = str(row["sha256"]) == current[field]["sha256"]
            score = 1.0 if exact else content_similarity(field, content[field], str(row["normalized_text"]))
            if exact or score >= thresholds[field]:
                collisions.append({
                    "field": field,
                    "score": round(score, 4),
                    "exact": exact,
                    "conflicting_product_id": str(row["product_id"]),
                    "conflicting_asin": str(row["asin"]),
                    "conflicting_shopify_product_id": str(row["shopify_product_id"]),
                })
        return collisions

    def _validate_content_evidence(
        self,
        product: dict[str, Any],
        content_or_path: dict[str, Any] | Path,
    ) -> tuple[dict[str, str], str, dict[str, Any]]:
        """Validate product-local facts and visual grounding without cross-product work.

        Applied products already passed uniqueness before their apply task was created.
        Recovery only needs to prove their persisted artifacts are still internally
        valid before rebuilding a missing fingerprint index.
        """
        workspace = self.workspace(product)
        content = validate_content_grounding(content_or_path, workspace / "source.json")
        visual_path = workspace / "visual_analysis.json"
        if not visual_path.is_file():
            raise ContentValidationError("visual_analysis.json is required before content validation.")
        expected_digest = source_digest(workspace / "source.json")
        visual = validate_visual_analysis(
            visual_path,
            expected_task_id=product["id"],
            expected_source_digest=expected_digest,
        )
        validate_visual_keyword_usage(content, visual)
        return content, expected_digest, visual

    def _validate_complete_content(
        self,
        product: dict[str, Any],
        content_or_path: dict[str, Any] | Path,
        *,
        record_events: bool,
    ) -> dict[str, str]:
        workspace = self.workspace(product)
        content, expected_digest, visual = self._validate_content_evidence(product, content_or_path)
        collisions = self._content_collisions(product["id"], content)
        source_payload = load_json(workspace / "source.json")
        atomic_write_json(workspace / "content_validation.json", {
            "valid": not collisions,
            "source_digest": expected_digest,
            "visual_keywords": [*visual["design_keywords"], *visual["shape_keywords"]],
            "allowed_facts": {
                "source_title": str(source_payload.get("title") or ""),
                "visual_keywords": [*visual["design_keywords"], *visual["shape_keywords"]],
            },
            "collisions": collisions,
            "validated_at": utc_now(),
        })
        if collisions:
            if record_events:
                with self.transaction(immediate=True) as connection:
                    connection.execute(
                        "UPDATE content_tasks SET uniqueness_attempts=uniqueness_attempts+1, updated_at=? WHERE product_id=?",
                        (utc_now(), product["id"]),
                    )
                    self._event_conn(
                        connection, "content_collision", run_id=product["run_id"],
                        product_id=product["id"], source="mcp", asin=product["asin"],
                        collisions=collisions,
                        message="Content is too similar to an existing product and must be revised.",
                    )
            summary = "; ".join(
                f"{item['field']} vs {item['conflicting_asin']} ({item['score']:.2f})"
                for item in collisions[:8]
            )
            raise ContentValidationError("Content uniqueness collision: " + summary)
        if record_events:
            self.event(
                "content_unique", run_id=product["run_id"], product_id=product["id"],
                source="mcp", asin=product["asin"],
                message="Content passed cross-product uniqueness validation.",
            )
        return content

    def _store_content_fingerprints(
        self, connection: sqlite3.Connection, product_id: str, revision: int, content: dict[str, str]
    ) -> None:
        connection.execute("UPDATE content_fingerprints SET active=0 WHERE product_id=?", (product_id,))
        created_at = utc_now()
        for field, fingerprint in content_fingerprints(content).items():
            connection.execute(
                """
                INSERT OR REPLACE INTO content_fingerprints(
                    product_id, revision, field, normalized_text, sha256, signature_json, active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    product_id, revision, field, fingerprint["normalized"],
                    fingerprint["sha256"], _json({
                        "tokens": fingerprint["tokens"], "shingles": fingerprint["shingles"],
                    }), created_at,
                ),
            )

    def _finalize_paths(self, product: dict[str, Any]) -> dict[str, str]:
        workspace = self.workspace(product)
        draft = workspace / "content.temp.json"
        final = workspace / "content.json"
        if not draft.is_file():
            if final.is_file():
                return self._validate_complete_content(product, final, record_events=False)
            raise ContentValidationError("content.temp.json does not exist.")
        normalized = self._validate_complete_content(product, draft, record_events=True)
        draft.replace(final)
        return normalized

    def finalize_content(self, product_id: str, token: str) -> dict[str, Any]:
        product = self.require_claim(product_id, token)
        normalized = self._finalize_paths(product)
        self._mark_content_ready(product, token=token, content=normalized)
        return {"task_id": product_id, "state": "ready", "content": normalized}

    def _mark_content_ready(
        self,
        product: dict[str, Any],
        *,
        token: str | None = None,
        content: dict[str, str] | None = None,
    ) -> None:
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            if token is not None:
                row = self._require_claim_conn(connection, product["id"], token)
            else:
                row = connection.execute(
                    "SELECT revision FROM content_tasks WHERE product_id=?", (product["id"],)
                ).fetchone()
            if content is None:
                content = validate_content(self.workspace(product) / "content.json")
            self._store_content_fingerprints(connection, product["id"], int(row["revision"] if row else 0), content)
            connection.execute(
                """
                UPDATE content_tasks SET state='ready', claimed_at=NULL, claimed_by=NULL,
                    claim_token_hash=NULL, lease_expires_at=NULL, last_error=NULL,
                    last_agent_error=NULL, updated_at=?
                WHERE product_id=?
                """,
                (now, product["id"]),
            )
            connection.execute(
                """
                INSERT INTO apply_tasks(product_id, state, queued_at, updated_at)
                VALUES (?, 'queued', ?, ?)
                ON CONFLICT(product_id) DO UPDATE SET
                    state=CASE WHEN apply_tasks.state='applied' THEN 'applied' ELSE 'queued' END,
                    last_error=NULL, updated_at=excluded.updated_at
                """,
                (product["id"], now, now),
            )
            connection.execute(
                "UPDATE products SET status='apply_queued', error=NULL, error_type=NULL, updated_at=? WHERE id=?",
                (now, product["id"]),
            )
            self._event_conn(
                connection, "content_ready", run_id=product["run_id"], product_id=product["id"],
                source="mcp" if token else "dashboard", asin=product["asin"], status="content_ready",
            )
        with self._condition:
            self._condition.notify_all()

    def release_content(self, product_id: str, token: str, reason: str) -> dict[str, Any]:
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            row = self._require_claim_conn(connection, product_id, token)
            connection.execute(
                """
                UPDATE content_tasks SET state='queued', claimed_at=NULL, claimed_by=NULL,
                    claim_token_hash=NULL, lease_expires_at=NULL, last_error=?, updated_at=? WHERE product_id=?
                """,
                (reason, now, product_id),
            )
            connection.execute("UPDATE products SET status='content_queued', updated_at=? WHERE id=?", (now, product_id))
            self._event_conn(
                connection, "content_released", run_id=row["run_id"], product_id=product_id,
                source="mcp", asin=row["asin"], message=reason,
            )
        with self._condition:
            self._condition.notify_all()
        return {"task_id": product_id, "state": "queued"}

    def force_release_content(self, product_id: str, reason: str = "Released from dashboard.") -> dict[str, Any]:
        product = self.product(product_id)
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            row = connection.execute("SELECT state FROM content_tasks WHERE product_id=?", (product_id,)).fetchone()
            if not row:
                raise KeyError(product_id)
            if row["state"] != "claimed":
                raise QueueConflict("Only a currently claimed content task can be released.")
            connection.execute(
                """
                UPDATE content_tasks SET state='queued', claimed_at=NULL, claimed_by=NULL,
                    claim_token_hash=NULL, lease_expires_at=NULL, last_error=?, updated_at=? WHERE product_id=?
                """,
                (reason, now, product_id),
            )
            connection.execute("UPDATE products SET status='content_queued', updated_at=? WHERE id=?", (now, product_id))
            self._event_conn(
                connection, "content_released", run_id=product["run_id"], product_id=product_id,
                source="dashboard", asin=product["asin"], message=reason,
            )
        return self.product_status(self.product(product_id))

    def report_content_progress(self, product_id: str, token: str, message: str) -> dict[str, Any]:
        product = self.require_claim(product_id, token)
        clean = str(message).strip()[:1000]
        self.event(
            "content_progress", run_id=product["run_id"], product_id=product_id,
            source="mcp", asin=product["asin"], message=clean,
        )
        return {"task_id": product_id, "reported": True}

    def queue_status(self, run_id: str | None = None) -> dict[str, Any]:
        connection = self._connect()
        try:
            sql = (
                "SELECT ct.state, COUNT(*) AS count FROM content_tasks ct "
                "JOIN products p ON p.id=ct.product_id"
            )
            params: list[Any] = []
            if run_id:
                sql += " WHERE p.run_id=?"
                params.append(run_id)
            sql += " GROUP BY ct.state"
            content = {row["state"]: row["count"] for row in connection.execute(sql, params).fetchall()}
            apply_sql = (
                "SELECT at.state, COUNT(*) AS count FROM apply_tasks at "
                "JOIN products p ON p.id=at.product_id"
            )
            if run_id:
                apply_sql += " WHERE p.run_id=?"
            apply_sql += " GROUP BY at.state"
            apply = {row["state"]: row["count"] for row in connection.execute(apply_sql, params).fetchall()}
            failed_sql = "SELECT COUNT(*) FROM products WHERE status IN ('failed', 'needs_attention')"
            failed_params: list[Any] = []
            if run_id:
                failed_sql += " AND run_id=?"
                failed_params.append(run_id)
            failed = int(connection.execute(failed_sql, failed_params).fetchone()[0])
            last = connection.execute(
                "SELECT created_at, type, payload_json FROM events WHERE source='mcp' ORDER BY id DESC LIMIT 1"
            ).fetchone()
        finally:
            connection.close()
        return {
            "content": content,
            "apply": apply,
            "failed": failed,
            "last_mcp_activity": (self._public_value({"at": last["created_at"], "event": last["type"], **_loads(last["payload_json"], {})}) if last else None),
        }

    def content_task(self, product_id: str) -> dict[str, Any]:
        product = self.product(product_id)
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT state, queued_at, claimed_by, lease_expires_at, attempts, automation_attempts, "
                "last_agent_error, revision, last_error, source_digest, context_read_revision, "
                "visual_analysis_state, uniqueness_attempts "
                "FROM content_tasks WHERE product_id=?", (product_id,)
            ).fetchone()
        finally:
            connection.close()
        if not row:
            raise KeyError(product_id)
        workspace = self.workspace(product)
        draft = workspace / "content.temp.json"
        final = workspace / "content.json"
        content = load_json(final) if final.exists() else (load_json(draft) if draft.exists() else {})
        visual_path = workspace / "visual_analysis.json"
        validation_path = workspace / "content_validation.json"
        validation_error = None
        try:
            self._validate_complete_content(product, content, record_events=False)
        except ContentValidationError as exc:
            validation_error = str(exc)
        return {
            "task_id": product_id, "run_id": product["run_id"], "asin": product["asin"],
            **dict(row), "content": content, "is_final": final.exists(),
            "visual_analysis": load_json(visual_path) if visual_path.is_file() else None,
            "content_validation": load_json(validation_path) if validation_path.is_file() else None,
            "valid": validation_error is None, "validation_error": validation_error,
        }

    def save_manual_draft(self, product_id: str, content: dict[str, Any]) -> dict[str, Any]:
        task = self.content_task(product_id)
        if task["state"] != "queued" or task["is_final"]:
            raise QueueConflict("Only an unclaimed queued content draft can be edited.")
        product = self.product(product_id)
        atomic_write_json(self.workspace(product) / "content.temp.json", content)
        self.event(
            "content_draft_saved", run_id=product["run_id"], product_id=product_id,
            source="dashboard", asin=product["asin"], message="content.temp.json saved atomically.",
        )
        return self.content_task(product_id)

    def finalize_manual_content(self, product_id: str) -> dict[str, Any]:
        task = self.content_task(product_id)
        if task["state"] != "queued" or task["is_final"]:
            raise QueueConflict("Only an unclaimed queued content draft can be finalized.")
        product = self.product(product_id)
        normalized = self._finalize_paths(product)
        self._mark_content_ready(product, content=normalized)
        return self.content_task(product_id)

    def return_content_to_queue(self, product_id: str) -> dict[str, Any]:
        product = self.product(product_id)
        if product["status"] not in {"apply_queued", "needs_attention"}:
            raise QueueConflict("Only unapplied content can be returned to the content queue.")
        task = self.content_task(product_id)
        if not task["is_final"]:
            raise QueueConflict("There is no finalized content to return to the queue.")
        workspace = self.workspace(product)
        progress_path = workspace / "apply_progress.json"
        progress = load_json(progress_path) if progress_path.exists() else {}
        if any(progress.get(key) for key in ("product_set", "new_media_ids", "media_verified", "old_media_deleted", "metafields_set", "published")):
            raise QueueConflict("Content is locked because a Shopify mutation checkpoint already exists.")
        final = workspace / "content.json"
        draft = workspace / "content.temp.json"
        if final.exists():
            final.replace(draft)
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            apply_row = connection.execute(
                "SELECT state FROM apply_tasks WHERE product_id=?", (product_id,)
            ).fetchone()
            if apply_row and apply_row["state"] == "running":
                raise QueueConflict("Shopify apply is already running; content is locked.")
            connection.execute(
                """
                UPDATE content_tasks SET state='queued', revision=revision+1, claimed_at=NULL,
                    claimed_by=NULL, claim_token_hash=NULL, lease_expires_at=NULL,
                    automation_attempts=0, last_agent_error=NULL, context_read_revision=NULL,
                    visual_analysis_state='pending', uniqueness_attempts=0, updated_at=? WHERE product_id=?
                """,
                (now, product_id),
            )
            connection.execute("UPDATE content_fingerprints SET active=0 WHERE product_id=?", (product_id,))
            connection.execute("DELETE FROM apply_tasks WHERE product_id=?", (product_id,))
            connection.execute(
                "UPDATE products SET status='content_queued', error=NULL, error_type=NULL, updated_at=? WHERE id=?",
                (now, product_id),
            )
            self._event_conn(
                connection, "content_requeued", run_id=product["run_id"], product_id=product_id,
                source="dashboard", asin=product["asin"], message="Content returned to the queue for revision.",
            )
        return self.content_task(product_id)

    def retry_failed_content(self, product_id: str) -> dict[str, Any]:
        """Retry an Agent/content failure that never produced content.json.

        This is intentionally separate from returning finalized content to the
        queue and from retrying Shopify. A new revision invalidates evidence
        reads and visual analysis created by the failed Agent session.
        """
        product = self.product(product_id)
        if product["status"] != "needs_attention":
            raise QueueConflict("Only a product needing attention can retry content generation.")
        task = self.content_task(product_id)
        if task["state"] != "error" or task["is_final"]:
            raise QueueConflict("Only an unfinished content Agent failure can retry content generation.")
        connection = self._connect()
        try:
            apply_row = connection.execute(
                "SELECT state FROM apply_tasks WHERE product_id=?", (product_id,)
            ).fetchone()
        finally:
            connection.close()
        if apply_row:
            raise QueueConflict("A Shopify apply task already exists; use Retry Shopify instead.")

        workspace = self.workspace(product)
        for filename in ("visual_analysis.json", "content_validation.json"):
            path = workspace / filename
            if path.is_file():
                path.unlink()
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE content_tasks SET state='queued', revision=revision+1,
                    claimed_at=NULL, claimed_by=NULL, claim_token_hash=NULL, lease_expires_at=NULL,
                    automation_attempts=0, last_agent_error=NULL, last_error=NULL,
                    context_read_revision=NULL, visual_analysis_state='pending',
                    uniqueness_attempts=0, updated_at=? WHERE product_id=?
                """,
                (now, product_id),
            )
            connection.execute(
                "UPDATE products SET status='content_queued', error=NULL, error_type=NULL, updated_at=? WHERE id=?",
                (now, product_id),
            )
            self._event_conn(
                connection, "content_retry_queued", run_id=product["run_id"], product_id=product_id,
                source="dashboard", asin=product["asin"],
                message="Failed content task queued for a fresh isolated Agent session.",
            )
        with self._condition:
            self._condition.notify_all()
        return self.content_task(product_id)

    def claim_next_apply(self) -> dict[str, Any] | None:
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            if connection.execute("SELECT 1 FROM apply_tasks WHERE state='running' LIMIT 1").fetchone():
                return None
            row = connection.execute(
                """
                SELECT at.product_id FROM apply_tasks at JOIN products p ON p.id=at.product_id
                WHERE at.state='queued' ORDER BY at.queued_at, p.ordinal LIMIT 1
                """
            ).fetchone()
            if not row:
                return None
            product_id = str(row["product_id"])
            product = connection.execute("SELECT run_id, asin FROM products WHERE id=?", (product_id,)).fetchone()
            connection.execute(
                "UPDATE apply_tasks SET state='running', started_at=?, attempts=attempts+1, updated_at=? WHERE product_id=?",
                (now, now, product_id),
            )
            connection.execute("UPDATE products SET status='applying', updated_at=? WHERE id=?", (now, product_id))
            self._event_conn(
                connection, "apply_started", run_id=product["run_id"], product_id=product_id,
                asin=product["asin"], status="applying",
            )
        return self.product(product_id)

    def finish_apply(self, product_id: str, status: str, *, error: str | None = None, error_type: str | None = None) -> None:
        if status not in {"applied", "dry_run_complete", "needs_attention", "failed"}:
            raise ValueError(f"Invalid apply result: {status}")
        product = self.product(product_id)
        now = utc_now()
        apply_state = "applied" if status in {"applied", "dry_run_complete"} else "needs_attention"
        with self.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE apply_tasks SET state=?, last_error=?, updated_at=? WHERE product_id=?",
                (apply_state, error, now, product_id),
            )
            connection.execute(
                "UPDATE products SET status=?, error=?, error_type=?, updated_at=? WHERE id=?",
                (status, error, error_type, now, product_id),
            )
            self._event_conn(
                connection, "product_status", run_id=product["run_id"], product_id=product_id,
                asin=product["asin"], status=status, error=error, error_type=error_type,
            )
        with self._condition:
            self._condition.notify_all()

    def retry_apply(self, product_id: str) -> dict[str, Any]:
        product = self.product(product_id)
        if product["status"] != "needs_attention":
            raise QueueConflict("Only a product needing attention can retry Shopify.")
        if not (self.workspace(product) / "content.json").is_file():
            raise QueueConflict("content.json is missing; return the task to the content queue.")
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            task = connection.execute(
                "SELECT state FROM apply_tasks WHERE product_id=?", (product_id,)
            ).fetchone()
            if not task or task["state"] != "needs_attention":
                raise QueueConflict("This product does not have a retryable Shopify task.")
            connection.execute(
                "UPDATE apply_tasks SET state='queued', last_error=NULL, queued_at=?, updated_at=? WHERE product_id=?",
                (now, now, product_id),
            )
            connection.execute(
                "UPDATE products SET status='apply_queued', error=NULL, error_type=NULL, updated_at=? WHERE id=?",
                (now, product_id),
            )
            self._event_conn(
                connection, "apply_retried", run_id=product["run_id"], product_id=product_id,
                source="dashboard", asin=product["asin"], message="Shopify retry queued from checkpoints.",
            )
        with self._condition:
            self._condition.notify_all()
        return self.product_status(self.product(product_id))

    def acknowledge_product(self, product_id: str) -> dict[str, Any]:
        product = self.product(product_id)
        if product["status"] != "needs_attention":
            raise QueueConflict("Only a product needing attention can be acknowledged and closed.")
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE products SET status='cancelled', updated_at=? WHERE id=?", (now, product_id)
            )
            connection.execute(
                "UPDATE content_tasks SET state='error', updated_at=? WHERE product_id=? AND state!='ready'",
                (now, product_id),
            )
            connection.execute(
                "UPDATE apply_tasks SET state='cancelled', updated_at=? WHERE product_id=?",
                (now, product_id),
            )
            self._event_conn(
                connection, "product_closed", run_id=product["run_id"], product_id=product_id,
                source="dashboard", asin=product["asin"], status="cancelled",
                message="Needs-attention task acknowledged and closed.",
            )
        return self.product_status(self.product(product_id))

    def recover(self, *, runtime_workers: bool = True) -> dict[str, int]:
        counts = {
            "crawls_interrupted": 0, "leases_expired": 0, "applies_requeued": 0,
            "content_reconciled": 0, "visual_reconciled": 0, "gallery_manifests_verified": 0,
        }
        now = utc_now()
        with self.transaction(immediate=True) as connection:
            counts["leases_expired"] = self._expire_leases_conn(connection)
            if runtime_workers:
                running = connection.execute("SELECT id FROM runs WHERE crawl_status='running'").fetchall()
                for row in running:
                    connection.execute("UPDATE runs SET crawl_status='interrupted', updated_at=? WHERE id=?", (now, row["id"]))
                    self._event_conn(connection, "crawl_status", run_id=row["id"], status="interrupted", message="Server restarted during crawl.")
                counts["crawls_interrupted"] = len(running)
                applies = connection.execute("SELECT product_id FROM apply_tasks WHERE state='running'").fetchall()
                for row in applies:
                    connection.execute(
                        "UPDATE apply_tasks SET state='queued', updated_at=? WHERE product_id=?", (now, row["product_id"])
                    )
                    connection.execute(
                        "UPDATE products SET status='apply_queued', updated_at=? WHERE id=?", (now, row["product_id"])
                    )
                counts["applies_requeued"] = len(applies)
        connection = self._connect()
        try:
            products = [self._product_dict(row) for row in connection.execute("SELECT * FROM products").fetchall()]
        finally:
            connection.close()
        for product in products:
            workspace = self.workspace(product)
            source_path = workspace / "source.json"
            visual = workspace / "visual_analysis.json"
            gallery_manifest = workspace / "evidence" / "gallery" / "manifest.json"
            evidence_root = (workspace / "evidence").resolve()

            def has_safe_evidence(evidence_id: str) -> bool:
                target = (evidence_root / evidence_id).resolve()
                return target != evidence_root and evidence_root in target.parents and target.is_file()

            if gallery_manifest.is_file():
                try:
                    gallery_payload = load_json(gallery_manifest)
                    evidence_ids = [
                        str(item.get("evidence_id") or "")
                        for item in gallery_payload.get("images", [])
                        if isinstance(item, dict)
                    ]
                    contact_id = str(gallery_payload.get("contact_sheet") or "")
                    if evidence_ids and contact_id and all(
                        has_safe_evidence(evidence_id)
                        for evidence_id in [contact_id, *evidence_ids]
                    ):
                        counts["gallery_manifests_verified"] += 1
                except (OSError, ValueError, TypeError):
                    pass
            if visual.is_file() and source_path.is_file():
                try:
                    expected_digest = source_digest(source_path)
                    visual_payload = validate_visual_analysis(
                        visual,
                        expected_task_id=product["id"],
                        expected_source_digest=expected_digest,
                    )
                    if all(
                        has_safe_evidence(str(evidence_id))
                        for evidence_id in visual_payload["evidence_ids"]
                    ):
                        with self.transaction(immediate=True) as connection:
                            row = connection.execute(
                                "SELECT source_digest, visual_analysis_state FROM content_tasks WHERE product_id=?",
                                (product["id"],),
                            ).fetchone()
                            if row and str(row["source_digest"] or expected_digest) == expected_digest:
                                if str(row["visual_analysis_state"]) != "ready":
                                    connection.execute(
                                        "UPDATE content_tasks SET source_digest=?, visual_analysis_state='ready', "
                                        "updated_at=? WHERE product_id=?",
                                        (expected_digest, utc_now(), product["id"]),
                                    )
                                    counts["visual_reconciled"] += 1
                except (ContentValidationError, OSError, ValueError, TypeError):
                    with self.transaction(immediate=True) as connection:
                        connection.execute(
                            "UPDATE content_tasks SET visual_analysis_state='pending', updated_at=? "
                            "WHERE product_id=? AND visual_analysis_state!='pending'",
                            (utc_now(), product["id"]),
                        )
            if product["status"] in FINAL_PRODUCT_STATES:
                final = workspace / "content.json"
                if product["status"] in {"applied", "dry_run_complete"} and final.is_file():
                    try:
                        normalized = (
                            self._validate_content_evidence(product, final)[0]
                            if visual.is_file()
                            else validate_content_grounding(final, workspace / "source.json")
                        )
                        with self.transaction(immediate=True) as connection:
                            row = connection.execute(
                                "SELECT revision FROM content_tasks WHERE product_id=?", (product["id"],)
                            ).fetchone()
                            self._store_content_fingerprints(
                                connection, product["id"], int(row["revision"] if row else 0), normalized
                            )
                    except ContentValidationError:
                        pass
                continue
            workspace = self.workspace(product)
            final = workspace / "content.json"
            draft = workspace / "content.temp.json"
            if final.exists():
                try:
                    normalized = self._validate_complete_content(product, final, record_events=False)
                except ContentValidationError:
                    continue
                if product["status"] not in {
                    "price_verified", "content_queued", "content_claimed", "content_ready", "apply_queued", "applying", "needs_attention"
                }:
                    continue
                connection = self._connect()
                try:
                    row = connection.execute("SELECT state FROM content_tasks WHERE product_id=?", (product["id"],)).fetchone()
                    apply_row = connection.execute(
                        "SELECT state FROM apply_tasks WHERE product_id=?", (product["id"],)
                    ).fetchone()
                finally:
                    connection.close()
                # A Shopify failure is deliberately user-gated. Reconciliation may
                # repair a missing queue row, but it must never turn a failed
                # mutation into an automatic retry merely because content.json is
                # still present on disk.
                if product["status"] == "needs_attention" or (
                    apply_row and apply_row["state"] == "needs_attention"
                ):
                    continue
                if apply_row and apply_row["state"] in {"queued", "running", "applied"}:
                    continue
                if not row:
                    self.enqueue_content(product["id"])
                self._mark_content_ready(product, content=normalized)
                counts["content_reconciled"] += 1
            elif draft.exists():
                connection = self._connect()
                try:
                    row = connection.execute("SELECT 1 FROM content_tasks WHERE product_id=?", (product["id"],)).fetchone()
                finally:
                    connection.close()
                if not row:
                    self.enqueue_content(product["id"])
                    counts["content_reconciled"] += 1
        return counts
