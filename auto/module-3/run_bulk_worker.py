"""
run_bulk_worker.py
Tiến trình Worker độc lập (Standalone Durable Background Worker Daemon)
xử lý các Job tạo sản phẩm hàng loạt (Bulk Product Creation) cho WRYDECO Shopify Admin.

Cách dùng:
  python run_bulk_worker.py --daemon
  python run_bulk_worker.py --job-id <JOB_ID>
"""

import os
import sys
import time
import uuid
import signal
import logging
import argparse
from datetime import datetime, timezone

import bulk_product_job_store as store
from bulk_product_worker import run_bulk_job_worker

logger = logging.getLogger("bulk_worker_daemon")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [PID:%(process)d] %(name)s: %(message)s"
)

IS_RUNNING = True


def handle_shutdown_signal(signum, frame):
    global IS_RUNNING
    logger.info(f"Nhận tín hiệu dừng ({signum}). Đang hoàn tất công việc hiện tại trước khi tắt...")
    IS_RUNNING = False


signal.signal(signal.SIGINT, handle_shutdown_signal)
signal.signal(signal.SIGTERM, handle_shutdown_signal)


def run_daemon_loop(db_path: str = None, poll_interval: float = 2.0):
    worker_id = f"daemon_worker_{os.getpid()}_{uuid.uuid4().hex[:6]}"
    hostname = os.environ.get("HOSTNAME") or os.environ.get("COMPUTERNAME") or "localhost"
    logger.info(f"Khởi động Bulk Worker Daemon [{worker_id}] trên host '{hostname}' (DB: {db_path or store.DB_PATH})")

    while IS_RUNNING:
        try:
            # Ghi nhận nhịp tim heartbeat
            store.record_worker_heartbeat(
                worker_id=worker_id,
                hostname=hostname,
                pid=os.getpid(),
                status="idle",
                metadata={"mode": "daemon", "db": db_path or store.DB_PATH},
                db_path=db_path
            )

            # Quét tìm Job có trạng thái READY hoặc RUNNING
            conn = store.get_db_connection(db_path)
            try:
                row = conn.execute("""
                    SELECT job_id, status FROM bulk_jobs
                    WHERE status IN ('READY', 'RUNNING')
                    ORDER BY created_at ASC
                    LIMIT 1
                """).fetchone()
            finally:
                conn.close()

            if row:
                job_id = row["job_id"]
                logger.info(f"Tìm thấy Job cần thực thi: {job_id} (Status: {row['status']})")
                store.record_worker_heartbeat(
                    worker_id=worker_id,
                    hostname=hostname,
                    pid=os.getpid(),
                    status="busy",
                    metadata={"active_job_id": job_id},
                    db_path=db_path
                )
                run_bulk_job_worker(job_id=job_id, worker_id=worker_id, db_path=db_path)
            else:
                time.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Lỗi ngoại lệ trong daemon loop: {str(e)}", exc_info=True)
            time.sleep(poll_interval)

    logger.info(f"Bulk Worker Daemon [{worker_id}] đã dừng an toàn.")


def main():
    parser = argparse.ArgumentParser(description="WRYDECO Bulk Product Worker Daemon")
    parser.add_argument("--daemon", action="store_true", help="Chạy ở chế độ daemon background liên tục")
    parser.add_argument("--job-id", type=str, help="Xử lý một Job ID cụ thể rồi thoát")
    parser.add_argument("--db-path", type=str, default=None, help="Đường dẫn file database SQLite")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Chu kỳ kiểm tra Job (giây)")

    args = parser.parse_args()

    if args.job_id:
        worker_id = f"cli_worker_{os.getpid()}_{uuid.uuid4().hex[:6]}"
        logger.info(f"Chạy Job đơn lẻ: {args.job_id} [Worker: {worker_id}]")
        res = run_bulk_job_worker(job_id=args.job_id, worker_id=worker_id, db_path=args.db_path)
        logger.info(f"Kết quả Job: {res.get('status')} (Success: {res.get('success_items')}, Failed: {res.get('failed_items')})")
    else:
        run_daemon_loop(db_path=args.db_path, poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
