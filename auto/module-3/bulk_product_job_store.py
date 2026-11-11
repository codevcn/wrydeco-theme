"""
bulk_product_job_store.py
Quản lý lưu trữ SQLite bền vững (Durable SQLite Persistent Store) cho các tác vụ
tạo sản phẩm hàng loạt (Bulk Product Creation Jobs) trên WRYDECO Shopify Admin.

Lưu trữ:
1. bulk_jobs: Thông tin tổng quan của từng Job (store_type, status, tiến độ, thời gian).
2. bulk_job_items: Từng sản phẩm cần tạo trong Job kèm payload, trạng thái và kết quả.
3. bulk_job_events: Chuỗi sự kiện có thứ tự tăng dần (Monotonic Event IDs) phục vụ SSE & Reconnect.
"""

import os
import sqlite3
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Xác định đường dẫn Database bền vững
DEFAULT_DB_DIR = "/var/lib/shopify-admin"
if os.path.exists(DEFAULT_DB_DIR) and os.access(DEFAULT_DB_DIR, os.W_OK):
    DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "bulk_jobs.sqlite3")
else:
    # Fallback cho môi trường local development và unit tests
    LOCAL_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    DEFAULT_DB_PATH = os.path.join(LOCAL_DATA_DIR, "bulk_jobs.sqlite3")

DB_PATH = os.environ.get("BULK_JOBS_DB_PATH", DEFAULT_DB_PATH)


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Tạo hoặc lấy kết nối SQLite với Row Factory để truy vấn dạng Dict."""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Kích hoạt WAL mode để hỗ trợ đọc/ghi đồng thời mượt mà
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: Optional[str] = None):
    """Khởi tạo schema bảng SQLite cho Bulk Product Jobs."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS bulk_jobs (
                job_id TEXT PRIMARY KEY,
                store_type TEXT NOT NULL,
                status TEXT NOT NULL,
                total_items INTEGER DEFAULT 0,
                completed_items INTEGER DEFAULT 0,
                success_items INTEGER DEFAULT 0,
                failed_items INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                metadata_json TEXT
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS bulk_job_items (
                item_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                client_item_id TEXT,
                item_index INTEGER NOT NULL,
                handle TEXT NOT NULL,
                title TEXT,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                product_id TEXT,
                links_json TEXT,
                error_code TEXT,
                error_message TEXT,
                errors_json TEXT,
                attempts INTEGER DEFAULT 0,
                worker_id TEXT,
                locked_at TEXT,
                lease_expires_at TEXT,
                idempotency_key TEXT UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES bulk_jobs(job_id) ON DELETE CASCADE,
                UNIQUE (job_id, item_index)
            );
            """)

            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bulk_job_items_job_status 
            ON bulk_job_items (job_id, status);
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS bulk_job_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES bulk_jobs(job_id) ON DELETE CASCADE
            );
            """)

            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bulk_job_events_job_id 
            ON bulk_job_events (job_id, event_id);
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS bulk_worker_heartbeats (
                worker_id TEXT PRIMARY KEY,
                hostname TEXT,
                pid INTEGER,
                last_heartbeat TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata_json TEXT
            );
            """)

            # Tự động cập nhật cột mới nếu DB đã tồn tại trước đó
            for col in ["worker_id TEXT", "locked_at TEXT", "lease_expires_at TEXT", "idempotency_key TEXT UNIQUE"]:
                try:
                    conn.execute(f"ALTER TABLE bulk_job_items ADD COLUMN {col};")
                except sqlite3.OperationalError:
                    pass
    finally:
        conn.close()


# Tự động khởi tạo DB khi module được import
init_db()


def create_job_record(
    job_id: str,
    store_type: str,
    items: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Tạo mới một Job và toàn bộ Items tương ứng trong database một cách nguyên tử."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                INSERT INTO bulk_jobs (
                    job_id, store_type, status, total_items, 
                    completed_items, success_items, failed_items,
                    created_at, updated_at, metadata_json
                ) VALUES (?, ?, ?, ?, 0, 0, 0, ?, ?, ?)
            """, (
                job_id,
                store_type,
                "READY",
                len(items),
                now_iso,
                now_iso,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))

            for idx, item in enumerate(items):
                item_id = item.get("item_id") or f"{job_id}:{idx}"
                client_item_id = item.get("client_item_id") or ""
                payload = item.get("payload") or {}
                handle = payload.get("handle") or f"unnamed-{idx}"
                title = payload.get("title") or ""
                initial_status = item.get("initial_status") or "PENDING"
                initial_errors = item.get("initial_errors") or []
                error_code = initial_errors[0].get("code") if initial_errors else None
                error_message = initial_errors[0].get("message") if initial_errors else None

                idempotency_key = item.get("idempotency_key") or f"{job_id}:{idx}"

                conn.execute("""
                    INSERT INTO bulk_job_items (
                        item_id, job_id, client_item_id, item_index,
                        handle, title, status, payload_json,
                        idempotency_key, error_code, error_message, errors_json,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_id,
                    job_id,
                    client_item_id,
                    idx,
                    handle,
                    title,
                    initial_status,
                    json.dumps(payload, ensure_ascii=False),
                    idempotency_key,
                    error_code,
                    error_message,
                    json.dumps(initial_errors, ensure_ascii=False) if initial_errors else None,
                    now_iso,
                    now_iso
                ))

            # Ghi nhận event khởi tạo Job
            conn.execute("""
                INSERT INTO bulk_job_events (job_id, event_type, data_json, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                job_id,
                "job_prepared",
                json.dumps({
                    "job_id": job_id,
                    "store_type": store_type,
                    "total": len(items),
                    "status": "READY"
                }, ensure_ascii=False),
                now_iso
            ))

        return get_job(job_id, db_path=db_path)
    finally:
        conn.close()


def get_job(job_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Truy vấn thông tin chi tiết một Job kèm danh sách items."""
    conn = get_db_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM bulk_jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not row:
            return None

        job_dict = dict(row)
        if job_dict.get("metadata_json"):
            job_dict["metadata"] = json.loads(job_dict["metadata_json"])

        # Lấy items
        item_rows = conn.execute(
            "SELECT * FROM bulk_job_items WHERE job_id = ? ORDER BY item_index ASC", 
            (job_id,)
        ).fetchall()

        items = []
        for ir in item_rows:
            idict = dict(ir)
            if idict.get("payload_json"):
                idict["payload"] = json.loads(idict["payload_json"])
            if idict.get("links_json"):
                idict["links"] = json.loads(idict["links_json"])
            if idict.get("errors_json"):
                idict["errors"] = json.loads(idict["errors_json"])
            items.append(idict)

        job_dict["items"] = items

        # Tính toán progress thống kê
        total = job_dict["total_items"]
        completed = job_dict["completed_items"]
        job_dict["progress"] = {
            "total": total,
            "completed": completed,
            "success": job_dict["success_items"],
            "failed": job_dict["failed_items"],
            "pending": max(0, total - completed),
            "percent": round((completed / total * 100), 1) if total > 0 else 0
        }

        return job_dict
    finally:
        conn.close()


def update_job_status(
    job_id: str, 
    status: str, 
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    db_path: Optional[str] = None
) -> bool:
    """Cập nhật trạng thái tổng của Job."""
    conn = get_db_connection(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        with conn:
            if started_at:
                conn.execute(
                    "UPDATE bulk_jobs SET status = ?, started_at = ?, updated_at = ? WHERE job_id = ?",
                    (status, started_at, now_iso, job_id)
                )
            elif finished_at:
                conn.execute(
                    "UPDATE bulk_jobs SET status = ?, finished_at = ?, updated_at = ? WHERE job_id = ?",
                    (status, finished_at, now_iso, job_id)
                )
            else:
                conn.execute(
                    "UPDATE bulk_jobs SET status = ?, updated_at = ? WHERE job_id = ?",
                    (status, now_iso, job_id)
                )
        return True
    finally:
        conn.close()


def update_item_status(
    item_id: str,
    status: str,
    product_id: Optional[str] = None,
    links: Optional[Dict[str, str]] = None,
    errors: Optional[List[Dict[str, Any]]] = None,
    increment_attempts: bool = False,
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Cập nhật trạng thái một Item và tự động đồng bộ thống kê Job."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            # Lấy thông tin hiện tại của item
            item_row = conn.execute(
                "SELECT * FROM bulk_job_items WHERE item_id = ?", (item_id,)
            ).fetchone()
            if not item_row:
                return None

            job_id = item_row["job_id"]
            old_status = item_row["status"]

            err_code = errors[0].get("code") if errors else None
            err_msg = errors[0].get("message") if errors else None

            # Cập nhật item
            attempt_sql = "attempts = attempts + 1," if increment_attempts else ""
            conn.execute(f"""
                UPDATE bulk_job_items 
                SET status = ?,
                    product_id = COALESCE(?, product_id),
                    links_json = COALESCE(?, links_json),
                    error_code = ?,
                    error_message = ?,
                    errors_json = ?,
                    {attempt_sql}
                    updated_at = ?
                WHERE item_id = ?
            """, (
                status,
                product_id,
                json.dumps(links, ensure_ascii=False) if links else None,
                err_code,
                err_msg,
                json.dumps(errors, ensure_ascii=False) if errors else None,
                now_iso,
                item_id
            ))

            # Cập nhật thống kê của Job nếu item chuyển sang trạng thái kết thúc (SUCCESS / FAILED)
            was_completed = old_status in ("SUCCESS", "FAILED", "FAILED_VALIDATION")
            is_now_completed = status in ("SUCCESS", "FAILED", "FAILED_VALIDATION")

            if not was_completed and is_now_completed:
                if status == "SUCCESS":
                    conn.execute("""
                        UPDATE bulk_jobs 
                        SET completed_items = completed_items + 1,
                            success_items = success_items + 1,
                            updated_at = ?
                        WHERE job_id = ?
                    """, (now_iso, job_id))
                else:
                    conn.execute("""
                        UPDATE bulk_jobs 
                        SET completed_items = completed_items + 1,
                            failed_items = failed_items + 1,
                            updated_at = ?
                        WHERE job_id = ?
                    """, (now_iso, job_id))

        return get_job(job_id, db_path=db_path)
    finally:
        conn.close()


def append_job_event(
    job_id: str,
    event_type: str,
    data: Dict[str, Any],
    db_path: Optional[str] = None
) -> int:
    """Ghi một event mới có thứ tự tăng dần vào bảng bulk_job_events."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("""
                INSERT INTO bulk_job_events (job_id, event_type, data_json, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                job_id,
                event_type,
                json.dumps(data, ensure_ascii=False),
                now_iso
            ))
            return cursor.lastrowid
    finally:
        conn.close()


def get_events_after(
    job_id: str, 
    last_event_id: int = 0, 
    limit: int = 200,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Lấy danh sách các events mới nhất sau một event_id (phục vụ SSE Reconnect / Last-Event-ID)."""
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute("""
            SELECT event_id, job_id, event_type, data_json, created_at
            FROM bulk_job_events
            WHERE job_id = ? AND event_id > ?
            ORDER BY event_id ASC
            LIMIT ?
        """, (job_id, last_event_id, limit)).fetchall()

        events = []
        for r in rows:
            events.append({
                "event_id": r["event_id"],
                "job_id": r["job_id"],
                "event_type": r["event_type"],
                "data": json.loads(r["data_json"]),
                "created_at": r["created_at"]
            })
        return events
    finally:
        conn.close()


def get_next_queued_item(job_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Lấy sản phẩm tiếp theo đang ở trạng thái QUEUED hoặc PENDING để xử lý."""
    conn = get_db_connection(db_path)
    try:
        row = conn.execute("""
            SELECT * FROM bulk_job_items 
            WHERE job_id = ? AND status IN ('QUEUED', 'PENDING')
            ORDER BY item_index ASC
            LIMIT 1
        """, (job_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        if res.get("payload_json"):
            res["payload"] = json.loads(res["payload_json"])
        return res
    finally:
        conn.close()


def claim_next_queued_item(
    job_id: str, 
    worker_id: str, 
    lease_seconds: int = 120, 
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Atomic Lease Claim: Worker giành quyền xử lý (claim lease) sản phẩm tiếp theo.
    Chuyển trạng thái sang CREATING và gán worker_id kèm hạn lease_expires_at.
    Ngăn chặn tuyệt đối 2 worker cùng chạy 1 item (Concurrency / Race Condition Guard).
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    lease_expires_iso = datetime.fromtimestamp(now.timestamp() + lease_seconds, timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            # Tìm candidate item: QUEUED/PENDING hoặc CREATING nhưng lease đã hết hạn
            row = conn.execute("""
                SELECT item_id, item_index FROM bulk_job_items
                WHERE job_id = ? AND (
                    status IN ('QUEUED', 'PENDING') OR 
                    (status = 'CREATING' AND lease_expires_at IS NOT NULL AND lease_expires_at < ?)
                )
                ORDER BY item_index ASC
                LIMIT 1
            """, (job_id, now_iso)).fetchone()
            if not row:
                return None

            target_item_id = row["item_id"]
            conn.execute("""
                UPDATE bulk_job_items
                SET status = 'CREATING',
                    worker_id = ?,
                    locked_at = ?,
                    lease_expires_at = ?,
                    attempts = attempts + 1,
                    updated_at = ?
                WHERE item_id = ?
            """, (worker_id, now_iso, lease_expires_iso, now_iso, target_item_id))

            claimed_row = conn.execute(
                "SELECT * FROM bulk_job_items WHERE item_id = ?", (target_item_id,)
            ).fetchone()
            if not claimed_row:
                return None
            res = dict(claimed_row)
            if res.get("payload_json"):
                res["payload"] = json.loads(res["payload_json"])
            return res
    finally:
        conn.close()


def recover_stale_in_flight_items(job_id: str, db_path: Optional[str] = None) -> int:
    """
    Worker Restart Recovery: Khôi phục tất cả các item bị kẹt ở CREATING 
    (do worker bị kill đột ngột hoặc crash) trở lại trạng thái QUEUED.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("""
                UPDATE bulk_job_items
                SET status = 'QUEUED',
                    worker_id = NULL,
                    lease_expires_at = NULL,
                    updated_at = ?
                WHERE job_id = ? AND status = 'CREATING'
            """, (now_iso, job_id))
            return cursor.rowcount
    finally:
        conn.close()


def record_worker_heartbeat(
    worker_id: str, 
    hostname: str = "", 
    pid: int = 0, 
    status: str = "active", 
    metadata: Optional[Dict[str, Any]] = None,
    db_path: Optional[str] = None
):
    """Ghi nhận nhịp tim heartbeat bền vững của background worker vào SQLite."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                INSERT INTO bulk_worker_heartbeats (
                    worker_id, hostname, pid, last_heartbeat, status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(worker_id) DO UPDATE SET
                    last_heartbeat = excluded.last_heartbeat,
                    status = excluded.status,
                    metadata_json = excluded.metadata_json;
            """, (
                worker_id, hostname, pid, now_iso, status, 
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
    finally:
        conn.close()


def get_worker_health(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Kiểm tra sức khỏe tổng thể của Worker subsystem qua database heartbeat."""
    conn = get_db_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM bulk_worker_heartbeats ORDER BY last_heartbeat DESC LIMIT 5"
        ).fetchall()
        active_workers = []
        now = datetime.now(timezone.utc)
        for r in rows:
            w_dict = dict(r)
            try:
                lh = datetime.fromisoformat(w_dict["last_heartbeat"])
                age_sec = (now - lh).total_seconds()
            except Exception:
                age_sec = 9999
            w_dict["age_seconds"] = round(age_sec, 1)
            w_dict["is_alive"] = age_sec < 60
            active_workers.append(w_dict)

        return {
            "status": "healthy" if any(w["is_alive"] for w in active_workers) else "idle_or_waiting",
            "workers": active_workers,
            "db_path": db_path or DB_PATH
        }
    finally:
        conn.close()
