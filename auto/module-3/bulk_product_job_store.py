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
import time
import uuid
import sqlite3
import json
import threading
import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Xác định đường dẫn Database bền vững và Bản lưu trữ tạo gần nhất (JSON)
DEFAULT_DB_DIR = "/var/lib/shopify-admin"
if os.path.exists(DEFAULT_DB_DIR) and os.access(DEFAULT_DB_DIR, os.W_OK):
    DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "bulk_jobs.sqlite3")
    DEFAULT_LATEST_ARCHIVE_PATH = os.path.join(DEFAULT_DB_DIR, "latest_create_archive.json")
else:
    # Fallback cho môi trường local development và unit tests
    LOCAL_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    DEFAULT_DB_PATH = os.path.join(LOCAL_DATA_DIR, "bulk_jobs.sqlite3")
    DEFAULT_LATEST_ARCHIVE_PATH = os.path.join(LOCAL_DATA_DIR, "latest_create_archive.json")

DB_PATH = os.environ.get("BULK_JOBS_DB_PATH", DEFAULT_DB_PATH)
_ARCHIVE_FILE_LOCK = threading.Lock()


@contextmanager
def job_execution_lock(job_id: str, db_path: Optional[str] = None):
    """One executor per job across web threads and daemon processes; crash releases it."""
    lock_dir = os.path.join(os.path.dirname(os.path.abspath(db_path or DB_PATH)), "bulk_job_locks")
    os.makedirs(lock_dir, exist_ok=True)
    lock_name = hashlib.sha256(job_id.encode("utf-8")).hexdigest() + ".lock"
    # Keep the file after release: unlinking a locked inode can allow two owners.
    with open(os.path.join(lock_dir, lock_name), "a+b") as lock_file:
        if os.name == "nt":
            import msvcrt
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            def acquire():
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            def release():
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            def acquire():
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            def release():
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        try:
            acquire()
        except (BlockingIOError, PermissionError):
            yield False
            return
        try:
            yield True
        finally:
            release()


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
            for col in ["worker_id TEXT", "locked_at TEXT", "lease_expires_at TEXT", "idempotency_key TEXT"]:
                try:
                    conn.execute(f"ALTER TABLE bulk_job_items ADD COLUMN {col};")
                except sqlite3.OperationalError:
                    pass

            try:
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_bulk_job_items_idempotency_key ON bulk_job_items (idempotency_key);")
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

        created_job = get_job(job_id, db_path=db_path, include_payload=True)
        try:
            sync_bulk_job_to_latest_archive(job_id=job_id, force_overwrite=True, db_path=db_path, job_snapshot=created_job)
        except Exception:
            pass
        return created_job
    finally:
        conn.close()


def get_job(job_id: str, db_path: Optional[str] = None, include_payload: bool = True) -> Optional[Dict[str, Any]]:
    """Truy vấn thông tin chi tiết một Job kèm danh sách items."""
    init_db(db_path)
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
            if include_payload:
                if idict.get("payload_json"):
                    idict["payload"] = json.loads(idict["payload_json"])
            else:
                idict.pop("payload_json", None)
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


def get_latest_job(
    store_type: Optional[str] = None,
    include_payload: bool = False,
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Truy vấn Bulk Job gần nhất theo store_type để hiển thị lại kết quả trên trang."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        if store_type:
            target_store = "custom" if str(store_type).lower() == "custom" else "default"
            row = conn.execute(
                "SELECT job_id FROM bulk_jobs WHERE store_type = ? ORDER BY created_at DESC LIMIT 1",
                (target_store,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT job_id FROM bulk_jobs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        latest_job_id = row["job_id"]
    finally:
        conn.close()

    return get_job(latest_job_id, db_path=db_path, include_payload=include_payload)


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
        try:
            sync_bulk_job_to_latest_archive(job_id=job_id, force_overwrite=False, db_path=db_path)
        except Exception:
            pass
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

        updated_job = get_job(job_id, db_path=db_path, include_payload=True)
        try:
            sync_bulk_job_to_latest_archive(job_id=job_id, force_overwrite=False, db_path=db_path, job_snapshot=updated_job)
        except Exception:
            pass
        return updated_job
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


# ==============================================================================
# BẢN LƯU TRỮ TẠO GẦN NHẤT (LATEST PRODUCT CREATION JSON ARCHIVE)
# ==============================================================================

def get_latest_create_archive_path(
    archive_path: Optional[str] = None,
    db_path: Optional[str] = None
) -> str:
    """
    Xác định đường dẫn file JSON lưu trữ bản tạo sản phẩm gần nhất trên máy chủ:
    1. Ưu tiên tham số archive_path tường minh.
    2. Ưu tiên biến môi trường LATEST_CREATE_ARCHIVE_PATH (phục vụ cô lập test / cấu hình riêng).
    3. Nếu truyền db_path tùy chỉnh khác DB_PATH mặc định (trong các unit test SQLite tạm),
       lưu file JSON cạnh db_path tạm đó để không ghi đè dữ liệu thật.
    4. Mặc định sử dụng DEFAULT_LATEST_ARCHIVE_PATH (/var/lib/shopify-admin/latest_create_archive.json
       hoặc data/latest_create_archive.json).
    """
    if archive_path and str(archive_path).strip():
        return str(archive_path).strip()

    env_path = os.environ.get("LATEST_CREATE_ARCHIVE_PATH", "").strip()
    if env_path:
        return env_path

    if db_path and os.path.abspath(db_path) != os.path.abspath(DB_PATH):
        return f"{os.path.abspath(db_path)}.latest_archive.json"

    return DEFAULT_LATEST_ARCHIVE_PATH


def _read_json_archive_file(target_path: str) -> Optional[Dict[str, Any]]:
    if not target_path or not os.path.exists(target_path):
        return None
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return None
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _atomic_write_json_archive_file(target_path: str, data: Dict[str, Any]) -> None:
    abs_target = os.path.abspath(target_path)
    parent_dir = os.path.dirname(abs_target)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    tmp_path = f"{abs_target}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    serialized = json.dumps(data, ensure_ascii=False, indent=2)

    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(serialized)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass

    last_err = None
    for attempt in range(5):
        try:
            os.replace(tmp_path, abs_target)
            return
        except PermissionError as pe:
            last_err = pe
            time.sleep(0.03 * (attempt + 1))
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass
    if last_err:
        raise last_err


def _summarize_archive_item_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "variant_count": 0,
            "media_count": 0,
            "thumbnail_url": "",
            "product_type": "",
            "status": "DRAFT",
            "price_preview": ""
        }
    media_list = payload.get("media") or []
    thumb_url = ""
    valid_media_count = 0
    for m in media_list:
        if isinstance(m, dict):
            u = str(m.get("url") or "").strip()
            if u:
                valid_media_count += 1
                if not thumb_url and (u.startswith("http://") or u.startswith("https://") or u.startswith("/")):
                    thumb_url = u
        elif isinstance(m, str) and m.strip():
            valid_media_count += 1
            if not thumb_url:
                thumb_url = m.strip()

    variants = payload.get("variants") or []
    prices = []
    for v in variants:
        if isinstance(v, dict) and v.get("price") is not None:
            try:
                prices.append(float(v["price"]))
            except (ValueError, TypeError):
                pass

    if len(prices) == 1:
        price_preview = f"${prices[0]:.2f}"
    elif len(prices) > 1:
        min_p, max_p = min(prices), max(prices)
        price_preview = f"${min_p:.2f}" if abs(max_p - min_p) < 0.005 else f"${min_p:.2f} - ${max_p:.2f}"
    else:
        price_preview = ""

    return {
        "variant_count": len(variants) if isinstance(variants, list) else 0,
        "media_count": valid_media_count if valid_media_count > 0 else (len(media_list) if isinstance(media_list, list) else 0),
        "thumbnail_url": thumb_url,
        "product_type": str(payload.get("productType") or "").strip(),
        "product_status": str(payload.get("status") or "DRAFT").strip().upper(),
        "price_preview": price_preview
    }


def _is_archive_item_failed(status: str) -> bool:
    st = str(status or "").strip().upper()
    return st in ("FAILED", "FAILED_VALIDATION", "ERROR")


def resolve_store_domain(store_type: str, explicit_domain: Optional[str] = None) -> str:
    """
    Xác định tên miền đầy đủ (.myshopify.com) của Store tương ứng với store_type ('default' hoặc 'custom')
    mà không tạo kết nối mạng ra ngoài.
    """
    if explicit_domain and str(explicit_domain).strip():
        raw = str(explicit_domain).strip().lower()
        raw = raw.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        if raw:
            return raw if "." in raw else f"{raw}.myshopify.com"

    norm_store = "custom" if str(store_type or "").strip().lower() == "custom" else "default"
    try:
        import proxy_manager
        if norm_store == "custom":
            logo_cfg = proxy_manager.load_logo_updater_config()
            raw_shop = proxy_manager.clean_shopify_domain(logo_cfg.get("shop_domain") or "")
            if raw_shop:
                return raw_shop if "." in raw_shop else f"{raw_shop}.myshopify.com"
            return "236qm8-w7.myshopify.com"
        raw_shop = proxy_manager.get_env_shopify_shop() or "wrydeco"
        return raw_shop if "." in raw_shop else f"{raw_shop}.myshopify.com"
    except Exception:
        return "236qm8-w7.myshopify.com" if norm_store == "custom" else "wrydeco.myshopify.com"


def save_latest_create_archive(
    mode: str,
    store_type: str,
    items: List[Dict[str, Any]],
    overall_status: str = "COMPLETED",
    job_id: Optional[str] = None,
    archive_id: Optional[str] = None,
    saved_at: Optional[str] = None,
    store_domain: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    archive_path: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Lưu toàn bộ dữ liệu sản phẩm và kết quả của lần tạo gần nhất (dù thành công hay thất bại)
    vào file JSON trên server (Bản lưu trữ tạo gần nhất).
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    norm_mode = "bulk" if str(mode or "").strip().lower() == "bulk" else "single"
    norm_store = "custom" if str(store_type or "").strip().lower() == "custom" else "default"
    meta_dict = metadata if isinstance(metadata, dict) else {}
    eff_store_domain = resolve_store_domain(norm_store, store_domain or meta_dict.get("store_domain"))
    eff_archive_id = archive_id or f"arc_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    eff_saved_at = saved_at or now_iso

    normalized_items: List[Dict[str, Any]] = []
    success_count = 0
    failed_count = 0

    for idx, raw_it in enumerate(items or []):
        it = raw_it if isinstance(raw_it, dict) else {}
        payload = it.get("payload") if isinstance(it.get("payload"), dict) else {}
        item_index = it.get("item_index") if isinstance(it.get("item_index"), int) else idx
        handle = str(it.get("handle") or payload.get("handle") or "").strip()
        title = str(it.get("title") or payload.get("title") or "").strip()
        st = str(it.get("status") or "PENDING").strip().upper()

        if st == "SUCCESS":
            success_count += 1
        elif _is_archive_item_failed(st):
            failed_count += 1

        errs = it.get("errors") if isinstance(it.get("errors"), list) else []
        err_msg = it.get("error_message")
        if not err_msg and errs:
            err_msg = " • ".join(
                f"[{e.get('field')}] {e.get('message')}" if isinstance(e, dict) and e.get("field") and e.get("field") not in ("unknown", "worker") else str(e.get("message") if isinstance(e, dict) else e)
                for e in errs if (isinstance(e, dict) and e.get("message")) or (isinstance(e, str) and e.strip())
            )
        err_code = it.get("error_code") or (errs[0].get("code") if errs and isinstance(errs[0], dict) else None)

        summary = _summarize_archive_item_payload(payload)
        normalized_items.append({
            "item_index": item_index,
            "handle": handle,
            "title": title,
            "status": st,
            "product_id": it.get("product_id"),
            "links": it.get("links") if isinstance(it.get("links"), dict) else None,
            "error_code": err_code,
            "error_message": str(err_msg).strip() if err_msg else None,
            "errors": errs,
            "summary": summary,
            "payload": payload
        })

    archive_doc = {
        "archive_id": eff_archive_id,
        "label": "Bản lưu trữ tạo gần nhất",
        "mode": norm_mode,
        "store_type": norm_store,
        "store_domain": eff_store_domain,
        "job_id": job_id,
        "overall_status": str(overall_status or "COMPLETED").strip().upper(),
        "saved_at": eff_saved_at,
        "updated_at": now_iso,
        "total_items": len(normalized_items),
        "completed_items": success_count + failed_count,
        "success_items": success_count,
        "failed_items": failed_count,
        "metadata": meta_dict,
        "items": normalized_items
    }

    target_file = get_latest_create_archive_path(archive_path=archive_path, db_path=db_path)
    with _ARCHIVE_FILE_LOCK:
        _atomic_write_json_archive_file(target_file, archive_doc)

    return archive_doc


def sync_bulk_job_to_latest_archive(
    job_id: str,
    force_overwrite: bool = False,
    archive_path: Optional[str] = None,
    db_path: Optional[str] = None,
    job_snapshot: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Đồng bộ trạng thái và toàn bộ dữ liệu sản phẩm của một Bulk Job sang file JSON
    của Bản lưu trữ tạo gần nhất.
    - Khi tạo Bulk Job mới (force_overwrite=True): luôn ghi đè thành bản lưu gần nhất mới.
    - Khi Worker cập nhật tiến độ (force_overwrite=False): chỉ cập nhật nếu bản lưu gần nhất
      hiện tại đang thuộc về chính job_id này (hoặc chưa có bản lưu nào).
    """
    target_file = get_latest_create_archive_path(archive_path=archive_path, db_path=db_path)
    existing = _read_json_archive_file(target_file)

    if not force_overwrite and existing is not None:
        if existing.get("job_id") != job_id:
            return existing

    job = job_snapshot if (job_snapshot and job_snapshot.get("items") and "payload" in (job_snapshot["items"][0] if job_snapshot["items"] else {})) else get_job(job_id, db_path=db_path, include_payload=True)
    if not job:
        return None

    items = job.get("items") or []
    total = len(items)
    invalid_only = total > 0 and all(_is_archive_item_failed(it.get("status")) for it in items)
    overall_status = "COMPLETED_WITH_ERRORS" if (invalid_only and job.get("status") == "READY") else (job.get("status") or "READY")

    preserved_archive_id = existing.get("archive_id") if (existing and existing.get("job_id") == job_id) else None
    preserved_saved_at = existing.get("saved_at") if (existing and existing.get("job_id") == job_id) else job.get("created_at")
    preserved_store_domain = existing.get("store_domain") if (existing and existing.get("job_id") == job_id) else None

    return save_latest_create_archive(
        mode="bulk",
        store_type=job.get("store_type") or "default",
        items=items,
        overall_status=overall_status,
        job_id=job_id,
        archive_id=preserved_archive_id,
        saved_at=preserved_saved_at,
        store_domain=preserved_store_domain,
        metadata=job.get("metadata") if isinstance(job.get("metadata"), dict) else {},
        archive_path=target_file,
        db_path=db_path
    )


def get_latest_create_archive(
    include_payload: bool = True,
    archive_path: Optional[str] = None,
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Đọc Bản lưu trữ tạo gần nhất từ file JSON trên máy chủ.
    Nếu file JSON mặc định chưa được khởi tạo nhưng trong SQLite đã có lịch sử Bulk Job gần nhất,
    tự động đồng bộ Job gần nhất đó sang file JSON để người dùng xem và tái sử dụng ngay lập tức.
    """
    explicit_override = bool(archive_path and str(archive_path).strip()) or bool(os.environ.get("LATEST_CREATE_ARCHIVE_PATH", "").strip())
    target_file = get_latest_create_archive_path(archive_path=archive_path, db_path=db_path)

    doc = _read_json_archive_file(target_file)
    if doc is None and not explicit_override:
        latest_job = get_latest_job(store_type=None, include_payload=True, db_path=db_path)
        if latest_job and latest_job.get("job_id"):
            doc = sync_bulk_job_to_latest_archive(
                job_id=latest_job["job_id"],
                force_overwrite=True,
                archive_path=target_file,
                db_path=db_path,
                job_snapshot=latest_job
            )

    if doc is None:
        return None

    if not doc.get("store_domain"):
        meta_dom = doc.get("metadata", {}).get("store_domain") if isinstance(doc.get("metadata"), dict) else None
        doc["store_domain"] = resolve_store_domain(doc.get("store_type") or "default", meta_dom)

    if not include_payload:
        slim_doc = dict(doc)
        slim_items = []
        for it in doc.get("items") or []:
            it_copy = dict(it)
            if "summary" not in it_copy and isinstance(it_copy.get("payload"), dict):
                it_copy["summary"] = _summarize_archive_item_payload(it_copy["payload"])
            it_copy.pop("payload", None)
            slim_items.append(it_copy)
        slim_doc["items"] = slim_items
        return slim_doc

    return doc

